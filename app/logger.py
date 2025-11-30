"""
CN5-Lite 日志系统

功能:
1. 基于loguru的日志管理
2. 文件日志轮转（按大小/时间）
3. 结构化日志
4. 性能监控装饰器
5. 敏感数据过滤
6. 日志压缩和保留
7. 异步日志
8. 请求上下文管理
"""

import os
import sys
import re
import time
import functools
import tracemalloc
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from contextvars import ContextVar
from loguru import logger

# ==================
# 全局变量
# ==================

_logger_initialized = False
_request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


# ==================
# 敏感数据过滤
# ==================

def filter_sensitive_data(message: str) -> str:
    """
    过滤日志中的敏感数据

    Args:
        message: 日志消息

    Returns:
        过滤后的消息
    """
    # API密钥模式
    patterns = [
        (r'(sk-[a-zA-Z0-9]{8})[a-zA-Z0-9]+', r'\1***'),  # OpenAI/DeepSeek API密钥
        (r'(Bearer\s+[a-zA-Z0-9]{8})[a-zA-Z0-9]+', r'\1***'),  # Bearer Token
        (r'password[\'"]?\s*[:=]\s*[\'"]?([a-zA-Z0-9]{3})[a-zA-Z0-9\'\"]*', r'password="\1***"'),  # 密码
        (r'token[\'"]?\s*[:=]\s*[\'"]?([a-zA-Z0-9]{3})[a-zA-Z0-9\'\"]*', r'token="\1***"'),  # Token
    ]

    for pattern, replacement in patterns:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)

    return message


def sensitive_filter(record: Dict[str, Any]) -> bool:
    """
    Loguru过滤器：过滤敏感数据

    Args:
        record: 日志记录

    Returns:
        是否记录该日志
    """
    # 过滤message字段
    if "message" in record:
        record["message"] = filter_sensitive_data(record["message"])

    # 过滤extra字段中可能的敏感数据
    if "extra" in record and isinstance(record["extra"], dict):
        for key, value in record["extra"].items():
            if isinstance(value, str):
                record["extra"][key] = filter_sensitive_data(value)

    return True


# ==================
# 模块过滤器
# ==================

def module_filter(modules: List[str]):
    """
    创建模块过滤器

    Args:
        modules: 允许的模块列表

    Returns:
        过滤器函数
    """
    def filter_func(record: Dict[str, Any]) -> bool:
        module_name = record.get("name", "")
        return any(module_name.startswith(mod) for mod in modules)
    return filter_func


# ==================
# 日志格式
# ==================

def get_log_format(with_context: bool = True) -> str:
    """
    获取日志格式

    Args:
        with_context: 是否包含请求上下文

    Returns:
        格式字符串
    """
    base_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    )

    if with_context:
        base_format += "<yellow>{extra}</yellow> | "

    base_format += "<level>{message}</level>"

    return base_format


# ==================
# 日志初始化
# ==================

def setup_logger(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "30 days",
    compression: Optional[str] = "zip",
    async_mode: bool = False,
    filter_modules: Optional[List[str]] = None
):
    """
    初始化日志系统

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（None则只输出到控制台）
        rotation: 日志轮转策略 ("10 MB" 或 "1 day")
        retention: 日志保留时间 ("30 days")
        compression: 压缩格式 ("zip" 或 None)
        async_mode: 是否启用异步日志
        filter_modules: 只记录特定模块的日志
    """
    global _logger_initialized

    # 移除默认handler
    logger.remove()

    # 添加控制台输出
    logger.add(
        sys.stderr,
        format=get_log_format(with_context=True),
        level=level,
        colorize=True,
        filter=sensitive_filter,
        enqueue=async_mode
    )

    # 添加文件输出
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 文件handler配置
        file_config = {
            "sink": log_file,
            "format": get_log_format(with_context=True),
            "level": level,
            "rotation": rotation,
            "retention": retention,
            "compression": compression,
            "encoding": "utf-8",
            "filter": sensitive_filter,
            "enqueue": async_mode
        }

        # 模块过滤
        if filter_modules:
            file_config["filter"] = lambda record: (
                sensitive_filter(record) and
                module_filter(filter_modules)(record)
            )

        logger.add(**file_config)

    _logger_initialized = True


def get_logger(name: str = __name__):
    """
    获取logger实例

    Args:
        name: logger名称（通常是模块名）

    Returns:
        logger实例
    """
    # 如果未初始化，使用默认配置初始化
    if not _logger_initialized:
        setup_logger()

    # 绑定模块名
    return logger.bind(name=name)


# ==================
# 请求上下文管理
# ==================

def set_request_context(**kwargs):
    """
    设置请求上下文

    Args:
        **kwargs: 上下文键值对 (request_id, user_id等)
    """
    context = _request_context.get()
    context.update(kwargs)
    _request_context.set(context)


def clear_context():
    """清除请求上下文"""
    _request_context.set({})


def get_context_logger(name: str = __name__):
    """
    获取带上下文的logger

    Args:
        name: logger名称

    Returns:
        绑定了上下文的logger
    """
    context = _request_context.get()
    return logger.bind(name=name, **context)


# ==================
# 性能监控装饰器
# ==================

def log_execution_time(func: Callable) -> Callable:
    """
    记录函数执行时间装饰器

    Args:
        func: 被装饰的函数

    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"{func.__name__} 执行完成",
                duration_ms=f"{duration_ms:.2f}",
                success=True
            )
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"{func.__name__} 执行失败",
                duration_ms=f"{duration_ms:.2f}",
                error=str(e),
                success=False
            )
            raise
    return wrapper


def log_memory_usage(func: Callable) -> Callable:
    """
    记录函数内存使用装饰器

    Args:
        func: 被装饰的函数

    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        try:
            result = func(*args, **kwargs)
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            logger.info(
                f"{func.__name__} 内存使用",
                current_mb=f"{current / 1024 / 1024:.2f}",
                peak_mb=f"{peak / 1024 / 1024:.2f}"
            )
            return result
        except Exception as e:
            tracemalloc.stop()
            logger.error(f"{func.__name__} 执行失败: {e}")
            raise
    return wrapper


# ==================
# 日志快捷函数
# ==================

def log_strategy_execution(strategy_id: int, **metrics):
    """
    记录策略执行日志

    Args:
        strategy_id: 策略ID
        **metrics: 指标数据
    """
    logger.info(
        f"策略执行",
        strategy_id=strategy_id,
        **metrics
    )


def log_trade(symbol: str, action: str, price: float, amount: float, **kwargs):
    """
    记录交易日志

    Args:
        symbol: 股票代码
        action: 交易动作 (buy/sell)
        price: 价格
        amount: 数量
        **kwargs: 其他参数
    """
    logger.info(
        f"交易执行: {action.upper()} {symbol}",
        symbol=symbol,
        action=action,
        price=price,
        amount=amount,
        **kwargs
    )


def log_risk_event(event_type: str, severity: str, **details):
    """
    记录风控事件

    Args:
        event_type: 事件类型
        severity: 严重程度 (low/medium/high/critical)
        **details: 详细信息
    """
    log_func = logger.warning if severity in ["low", "medium"] else logger.error

    log_func(
        f"风控事件: {event_type}",
        event_type=event_type,
        severity=severity,
        **details
    )

"""
CN5-Lite 配置管理

功能:
1. 从环境变量加载配置
2. 配置验证和类型转换
3. 默认值处理
4. 单例模式
5. 配置重载
6. 安全配置导出（隐藏敏感信息）
"""

import os
import re
from typing import List, Dict, Optional, Any
from pathlib import Path
from dotenv import load_dotenv

from app.errors import ConfigError


class Config:
    """配置管理类"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, env_file: Optional[str] = None, force_reload: bool = False):
        """
        初始化配置

        Args:
            env_file: .env文件路径（可选）
            force_reload: 强制重新加载（用于测试）
        """
        # 防止重复初始化（除非强制重载）
        if self._initialized and not force_reload:
            return

        # 加载.env文件
        if env_file:
            load_dotenv(env_file, override=True)
        else:
            # 默认加载项目根目录的.env
            root_dir = Path(__file__).parent.parent
            env_path = root_dir / ".env"
            if env_path.exists():
                load_dotenv(env_path, override=True)

        # 加载配置
        self._load_config()

        # 验证配置
        self._validate_config()

        self._initialized = True

    def _load_config(self):
        """从环境变量加载配置"""
        # ==================
        # 数据库配置
        # ==================
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://cn5user:cn5pass@localhost:5432/cn5lite"
        )

        self.REDIS_URL = os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0"
        )

        # ==================
        # AI模型配置
        # ==================
        self.AI_API_KEY = os.getenv("AI_API_KEY", "")
        self.AI_BASE_URL = os.getenv(
            "AI_BASE_URL",
            "https://api.deepseek.com/v1"
        )
        self.AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")

        # ==================
        # 数据源配置
        # ==================
        priority_str = os.getenv("DATA_SOURCE_PRIORITY", "akshare,baostock,efinance")
        self.DATA_SOURCE_PRIORITY = [s.strip() for s in priority_str.split(",")]

        cache_days = os.getenv("DATA_CACHE_DAYS", "30")
        try:
            self.DATA_CACHE_DAYS = int(cache_days)
        except ValueError:
            raise ConfigError(f"DATA_CACHE_DAYS必须是整数，当前值: {cache_days}")

        # ==================
        # 风控配置
        # ==================
        self.DAILY_LOSS_LIMIT_RATIO = self._parse_ratio(
            "DAILY_LOSS_LIMIT_RATIO",
            default=0.05
        )
        self.MAX_POSITION_RATIO = self._parse_ratio(
            "MAX_POSITION_RATIO",
            default=0.20
        )
        self.TOTAL_STOP_LOSS_RATIO = self._parse_ratio(
            "TOTAL_STOP_LOSS_RATIO",
            default=0.10
        )

        # ==================
        # 交易模式
        # ==================
        self.TRADING_MODE = os.getenv("TRADING_MODE", "simulation")

    def _parse_ratio(self, key: str, default: float) -> float:
        """
        解析比例配置（0-1之间）

        Args:
            key: 环境变量名
            default: 默认值

        Returns:
            比例值

        Raises:
            ConfigError: 比例超出范围
        """
        value_str = os.getenv(key)
        if value_str is None:
            return default

        try:
            value = float(value_str)
        except ValueError:
            raise ConfigError(f"{key}必须是数字，当前值: {value_str}")

        if not (0 < value <= 1):
            raise ConfigError(f"{key}比例必须在0-1之间，当前值: {value}")

        return value

    def _validate_config(self):
        """验证配置"""
        # 验证DATABASE_URL格式
        if not self.DATABASE_URL.startswith("postgresql://"):
            raise ConfigError(f"DATABASE_URL格式错误，必须以postgresql://开头")

        # 验证交易模式
        if self.TRADING_MODE not in ["simulation", "live"]:
            raise ConfigError(f"交易模式必须是simulation或live，当前值: {self.TRADING_MODE}")

        # 验证AI模型
        valid_models = ["deepseek-chat", "gpt-4", "gpt-4-turbo", "qwen-max", "qwen-plus"]
        if self.AI_MODEL not in valid_models:
            # 警告但不报错，允许使用其他模型
            pass

    def is_simulation_mode(self) -> bool:
        """是否模拟交易模式"""
        return self.TRADING_MODE == "simulation"

    def is_live_mode(self) -> bool:
        """是否实盘交易模式"""
        return self.TRADING_MODE == "live"

    def to_dict(self, safe: bool = True) -> Dict[str, Any]:
        """
        导出配置为字典

        Args:
            safe: 是否隐藏敏感信息

        Returns:
            配置字典
        """
        config_dict = {}

        # 获取所有大写属性（配置项）
        for key in dir(self):
            if key.isupper() and not key.startswith("_"):
                value = getattr(self, key)
                if safe:
                    value = self._mask_sensitive(key, value)
                config_dict[key] = value

        return config_dict

    def _mask_sensitive(self, key: str, value: Any) -> Any:
        """
        隐藏敏感信息

        Args:
            key: 配置键
            value: 配置值

        Returns:
            处理后的值
        """
        # 敏感字段列表
        sensitive_keys = ["API_KEY", "PASSWORD", "SECRET", "TOKEN"]

        # 检查是否包含敏感关键词
        if any(keyword in key for keyword in sensitive_keys):
            if isinstance(value, str) and len(value) > 3:
                # 保留前3个字符，其余用***替换
                return value[:3] + "***"
            return "***"

        # URL中的密码隐藏
        if "URL" in key and isinstance(value, str):
            # postgresql://user:password@host -> postgresql://user:***@host
            pattern = r"://([^:]+):([^@]+)@"
            return re.sub(pattern, r"://\1:***@", value)

        return value


# ==================
# 全局配置实例
# ==================

_global_config: Optional[Config] = None


def get_config() -> Config:
    """
    获取全局配置实例

    Returns:
        配置实例
    """
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


def reload_config(env_file: Optional[str] = None) -> Config:
    """
    重载配置

    Args:
        env_file: .env文件路径（可选）

    Returns:
        新的配置实例
    """
    global _global_config

    # 清除单例实例
    Config._instance = None
    _global_config = None

    # 重新创建
    _global_config = Config(env_file=env_file)
    return _global_config

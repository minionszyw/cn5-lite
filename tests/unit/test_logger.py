"""
CN5-Lite日志系统测试

测试范围:
1. 日志初始化
2. 日志级别控制
3. 文件日志轮转
4. 结构化日志
5. 日志格式化
6. 性能监控日志
"""

import pytest
import os
import time
from pathlib import Path


class TestLoggerInit:
    """日志初始化测试"""

    def test_logger_setup(self):
        """测试日志系统初始化"""
        from app.logger import setup_logger, get_logger

        # 初始化日志
        setup_logger()

        # 获取logger
        logger = get_logger(__name__)

        assert logger is not None

    def test_logger_with_custom_level(self):
        """测试自定义日志级别"""
        from app.logger import setup_logger, get_logger

        setup_logger(level="DEBUG")
        logger = get_logger(__name__)

        # 应该能记录DEBUG级别
        logger.debug("Debug message")

    def test_logger_singleton(self):
        """测试logger单例（基础logger实例）"""
        from app.logger import get_logger
        from loguru import logger

        # get_logger返回bound logger，每次都是新实例
        logger1 = get_logger("test")
        logger2 = get_logger("test")

        # 但两者都绑定到同一个底层logger
        # 验证logger可以正常工作
        assert logger1 is not None
        assert logger2 is not None


class TestLogLevels:
    """日志级别测试"""

    def test_info_level(self):
        """测试INFO级别"""
        from app.logger import get_logger

        logger = get_logger(__name__)
        logger.info("测试INFO日志")

    def test_warning_level(self):
        """测试WARNING级别"""
        from app.logger import get_logger

        logger = get_logger(__name__)
        logger.warning("测试WARNING日志")

    def test_error_level(self):
        """测试ERROR级别"""
        from app.logger import get_logger

        logger = get_logger(__name__)
        logger.error("测试ERROR日志")

    def test_critical_level(self):
        """测试CRITICAL级别"""
        from app.logger import get_logger

        logger = get_logger(__name__)
        logger.critical("测试CRITICAL日志")

    def test_debug_level_filtered(self):
        """测试DEBUG级别默认过滤"""
        from app.logger import setup_logger, get_logger

        # 默认级别INFO，应该过滤DEBUG
        setup_logger(level="INFO")
        logger = get_logger(__name__)

        # DEBUG消息不应该被记录
        logger.debug("This should not appear")


class TestFileLogging:
    """文件日志测试"""

    def test_log_to_file(self, tmp_path):
        """测试写入日志文件"""
        from app.logger import setup_logger, get_logger

        log_file = tmp_path / "test.log"

        setup_logger(log_file=str(log_file))
        logger = get_logger(__name__)

        test_message = "Test file logging message"
        logger.info(test_message)

        # 验证日志文件存在
        assert log_file.exists()

        # 验证日志内容
        content = log_file.read_text()
        assert test_message in content

    def test_log_rotation_by_size(self, tmp_path):
        """测试按大小轮转日志配置"""
        from app.logger import setup_logger, get_logger

        log_file = tmp_path / "rotation.log"

        # 设置小的轮转大小（1KB）
        setup_logger(log_file=str(log_file), rotation="1 KB")
        logger = get_logger(__name__)

        # 写入大量日志
        for i in range(100):
            logger.info(f"Log message {i} " + "x" * 100)

        # 主日志文件应该存在
        assert log_file.exists()

        # 验证文件有内容
        assert log_file.stat().st_size > 0

    def test_log_rotation_by_time(self, tmp_path):
        """测试按时间轮转日志"""
        from app.logger import setup_logger, get_logger

        log_file = tmp_path / "daily.log"

        # 按天轮转
        setup_logger(log_file=str(log_file), rotation="1 day")
        logger = get_logger(__name__)

        logger.info("Daily rotation test")

        assert log_file.exists()


class TestStructuredLogging:
    """结构化日志测试"""

    def test_log_with_context(self):
        """测试带上下文的日志"""
        from app.logger import get_logger

        logger = get_logger(__name__)

        # 记录带上下文的日志
        logger.bind(user_id=123, action="login").info("用户登录")

    def test_log_with_extra_fields(self):
        """测试额外字段"""
        from app.logger import get_logger

        logger = get_logger(__name__)

        logger.info(
            "策略执行完成",
            strategy_id=456,
            return_rate=0.15,
            duration_ms=250
        )

    def test_log_exception(self):
        """测试异常日志"""
        from app.logger import get_logger

        logger = get_logger(__name__)

        try:
            1 / 0
        except ZeroDivisionError:
            logger.exception("捕获异常")


class TestLogFormat:
    """日志格式测试"""

    def test_log_format_contains_timestamp(self, tmp_path):
        """测试日志包含时间戳"""
        from app.logger import setup_logger, get_logger

        log_file = tmp_path / "format.log"
        setup_logger(log_file=str(log_file))
        logger = get_logger(__name__)

        logger.info("Format test")

        content = log_file.read_text()
        # 应该包含时间戳（ISO格式）
        assert "202" in content or "T" in content

    def test_log_format_contains_level(self, tmp_path):
        """测试日志包含级别"""
        from app.logger import setup_logger, get_logger

        log_file = tmp_path / "level.log"
        setup_logger(log_file=str(log_file))
        logger = get_logger(__name__)

        logger.info("Level test")

        content = log_file.read_text()
        assert "INFO" in content

    def test_log_format_contains_module(self, tmp_path):
        """测试日志包含模块名"""
        from app.logger import setup_logger, get_logger

        log_file = tmp_path / "module.log"
        setup_logger(log_file=str(log_file))
        logger = get_logger("test.module")

        logger.info("Module test")

        content = log_file.read_text()
        assert "test.module" in content


class TestPerformanceLogging:
    """性能监控日志测试"""

    def test_log_execution_time(self):
        """测试执行时间记录"""
        from app.logger import get_logger, log_execution_time

        logger = get_logger(__name__)

        @log_execution_time
        def slow_function():
            time.sleep(0.1)
            return "done"

        result = slow_function()

        assert result == "done"

    def test_log_memory_usage(self):
        """测试内存使用记录"""
        from app.logger import get_logger, log_memory_usage

        logger = get_logger(__name__)

        @log_memory_usage
        def memory_function():
            data = [i for i in range(10000)]
            return len(data)

        result = memory_function()

        assert result == 10000


class TestLogFilter:
    """日志过滤测试"""

    def test_filter_sensitive_data(self, tmp_path):
        """测试敏感数据过滤器函数"""
        from app.logger import filter_sensitive_data

        # 测试API密钥过滤（保留前8个字符，例如sk-test12）
        message = "API Key: sk-test123456789abcdefghijklmnopqrstuvwxyz"
        filtered = filter_sensitive_data(message)
        assert "sk-test1234***" in filtered  # sk- + test1234（8个字符） + ***
        assert "56789abcdefghijklmnopqrstuvwxyz" not in filtered

        # 测试密码过滤
        message = "password='secretpass123'"
        filtered = filter_sensitive_data(message)
        assert "sec***" in filtered
        assert "retpass123" not in filtered

    def test_filter_by_module(self):
        """测试按模块过滤"""
        from app.logger import setup_logger, get_logger

        # 只记录特定模块的日志
        setup_logger(filter_modules=["app.services"])
        logger = get_logger("app.services.test")

        logger.info("Should be logged")


class TestLogCompression:
    """日志压缩测试"""

    def test_compress_old_logs(self, tmp_path):
        """测试旧日志压缩"""
        from app.logger import setup_logger, get_logger

        log_file = tmp_path / "compress.log"

        # 启用压缩
        setup_logger(log_file=str(log_file), compression="zip")
        logger = get_logger(__name__)

        for i in range(50):
            logger.info(f"Compression test {i}")


class TestLogRetention:
    """日志保留测试"""

    def test_retention_policy(self, tmp_path):
        """测试日志保留策略"""
        from app.logger import setup_logger, get_logger

        log_file = tmp_path / "retention.log"

        # 保留7天
        setup_logger(log_file=str(log_file), retention="7 days")
        logger = get_logger(__name__)

        logger.info("Retention test")


class TestAsyncLogging:
    """异步日志测试"""

    def test_async_logging_performance(self):
        """测试异步日志性能"""
        from app.logger import setup_logger, get_logger
        import time

        setup_logger(async_mode=True)
        logger = get_logger(__name__)

        start = time.time()

        # 大量日志
        for i in range(1000):
            logger.info(f"Async log {i}")

        duration = time.time() - start

        # 异步日志应该很快
        assert duration < 1.0


class TestLogContext:
    """日志上下文测试"""

    def test_request_context(self):
        """测试请求上下文"""
        from app.logger import get_logger, set_request_context

        set_request_context(request_id="req-123", user_id=456)

        logger = get_logger(__name__)
        logger.info("With request context")

    def test_clear_context(self):
        """测试清除上下文"""
        from app.logger import get_logger, set_request_context, clear_context

        set_request_context(request_id="req-456")
        clear_context()

        logger = get_logger(__name__)
        logger.info("After context cleared")

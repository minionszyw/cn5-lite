"""
CN5-Lite配置管理测试

测试范围:
1. 环境变量读取
2. 配置验证
3. 默认值处理
4. 类型转换
5. 配置覆盖
"""

import pytest
import os
from unittest.mock import patch


@pytest.fixture(autouse=True)
def reset_config():
    """每个测试前重置Config单例"""
    from app.config import Config
    Config._instance = None
    yield
    # 测试后也重置
    Config._instance = None


class TestConfig:
    """配置管理基础测试"""

    def test_load_from_env(self, monkeypatch):
        """测试从环境变量加载配置"""
        from app.config import Config

        # 设置环境变量
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
        monkeypatch.setenv("AI_API_KEY", "sk-test-key")

        config = Config()

        assert config.DATABASE_URL == "postgresql://test:test@localhost:5432/testdb"
        assert config.REDIS_URL == "redis://localhost:6379/1"
        assert config.AI_API_KEY == "sk-test-key"

    def test_default_values(self):
        """测试默认值"""
        from app.config import Config

        config = Config()

        # 数据库默认值
        assert config.DATABASE_URL.startswith("postgresql://")

        # AI模型默认值
        assert config.AI_MODEL in ["deepseek-chat", "gpt-4", "qwen-max"]

        # 交易模式默认值
        assert config.TRADING_MODE in ["simulation", "live"]

    def test_data_source_priority(self, monkeypatch):
        """测试数据源优先级配置"""
        from app.config import Config

        monkeypatch.setenv("DATA_SOURCE_PRIORITY", "baostock,akshare,efinance")

        config = Config()

        assert config.DATA_SOURCE_PRIORITY == ["baostock", "akshare", "efinance"]

    def test_cache_days_type_conversion(self, monkeypatch):
        """测试缓存天数类型转换"""
        from app.config import Config

        monkeypatch.setenv("DATA_CACHE_DAYS", "60")

        config = Config()

        assert isinstance(config.DATA_CACHE_DAYS, int)
        assert config.DATA_CACHE_DAYS == 60


class TestRiskConfig:
    """风控配置测试"""

    def test_risk_ratio_validation(self, monkeypatch):
        """测试风控比例验证"""
        from app.config import Config

        monkeypatch.setenv("DAILY_LOSS_LIMIT_RATIO", "0.05")
        monkeypatch.setenv("MAX_POSITION_RATIO", "0.20")
        monkeypatch.setenv("TOTAL_STOP_LOSS_RATIO", "0.10")

        config = Config()

        assert config.DAILY_LOSS_LIMIT_RATIO == 0.05
        assert config.MAX_POSITION_RATIO == 0.20
        assert config.TOTAL_STOP_LOSS_RATIO == 0.10

    def test_risk_ratio_bounds(self):
        """测试风控比例边界值"""
        from app.config import Config

        config = Config()

        # 比例应在0-1之间
        assert 0 < config.DAILY_LOSS_LIMIT_RATIO <= 1
        assert 0 < config.MAX_POSITION_RATIO <= 1
        assert 0 < config.TOTAL_STOP_LOSS_RATIO <= 1

    def test_invalid_risk_ratio(self, monkeypatch):
        """测试无效风控比例"""
        from app.config import Config
        from app.errors import ConfigError

        monkeypatch.setenv("DAILY_LOSS_LIMIT_RATIO", "1.5")  # 超过100%

        with pytest.raises(ConfigError, match="比例必须在0-1之间"):
            Config()


class TestTradingMode:
    """交易模式配置测试"""

    def test_simulation_mode(self, monkeypatch):
        """测试模拟交易模式"""
        from app.config import Config

        monkeypatch.setenv("TRADING_MODE", "simulation")

        config = Config()

        assert config.TRADING_MODE == "simulation"
        assert config.is_simulation_mode() is True
        assert config.is_live_mode() is False

    def test_live_mode(self, monkeypatch):
        """测试实盘交易模式"""
        from app.config import Config

        monkeypatch.setenv("TRADING_MODE", "live")

        config = Config()

        assert config.TRADING_MODE == "live"
        assert config.is_simulation_mode() is False
        assert config.is_live_mode() is True

    def test_invalid_trading_mode(self, monkeypatch):
        """测试无效交易模式"""
        from app.config import Config
        from app.errors import ConfigError

        monkeypatch.setenv("TRADING_MODE", "invalid")

        with pytest.raises(ConfigError, match="交易模式必须是simulation或live"):
            Config()


class TestAIConfig:
    """AI配置测试"""

    def test_ai_base_url_default(self):
        """测试AI Base URL默认值"""
        from app.config import Config

        config = Config()

        # 应该有默认的base_url
        assert config.AI_BASE_URL is not None

    def test_ai_base_url_custom(self, monkeypatch):
        """测试自定义AI Base URL"""
        from app.config import Config

        monkeypatch.setenv("AI_BASE_URL", "https://api.custom.com/v1")

        config = Config()

        assert config.AI_BASE_URL == "https://api.custom.com/v1"

    def test_ai_model_validation(self, monkeypatch):
        """测试AI模型验证"""
        from app.config import Config

        monkeypatch.setenv("AI_MODEL", "deepseek-chat")

        config = Config()

        assert config.AI_MODEL == "deepseek-chat"


class TestConfigReload:
    """配置重载测试"""

    def test_config_singleton(self):
        """测试配置单例模式"""
        from app.config import get_config

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_config_reload(self, monkeypatch):
        """测试配置重载"""
        from app.config import Config, reload_config

        # 初始配置
        config1 = Config()
        old_db_url = config1.DATABASE_URL

        # 修改环境变量
        monkeypatch.setenv("DATABASE_URL", "postgresql://new:new@localhost:5432/newdb")

        # 重载配置
        config2 = reload_config()

        assert config2.DATABASE_URL == "postgresql://new:new@localhost:5432/newdb"
        assert config2.DATABASE_URL != old_db_url


class TestConfigValidation:
    """配置验证测试"""

    def test_required_fields(self):
        """测试必填字段"""
        from app.config import Config

        config = Config()

        # 关键字段不能为空
        assert config.DATABASE_URL is not None
        assert config.REDIS_URL is not None

    def test_url_format_validation(self, monkeypatch):
        """测试URL格式验证"""
        from app.config import Config
        from app.errors import ConfigError

        monkeypatch.setenv("DATABASE_URL", "invalid-url")

        # 应该抛出格式错误
        with pytest.raises(ConfigError, match="DATABASE_URL格式错误"):
            Config(force_reload=True)

    def test_env_file_loading(self, tmp_path, reset_config):
        """测试从.env文件加载"""
        from app.config import Config
        import os

        # 创建临时.env文件
        env_file = tmp_path / ".env"
        env_file.write_text("""DATABASE_URL=postgresql://envfile:pass@localhost:5432/envdb
AI_API_KEY=sk-env-key
""")

        # 清除可能的环境变量干扰
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

        config = Config(env_file=str(env_file))

        assert "envfile" in config.DATABASE_URL


class TestConfigExport:
    """配置导出测试"""

    def test_export_safe_config(self):
        """测试导出安全配置（隐藏敏感信息）"""
        from app.config import Config

        config = Config()
        safe_config = config.to_dict(safe=True)

        # API密钥应被隐藏
        assert "***" in safe_config.get("AI_API_KEY", "")
        # 数据库密码应被隐藏
        assert "***" in safe_config.get("DATABASE_URL", "")

    def test_export_full_config(self):
        """测试导出完整配置"""
        from app.config import Config

        config = Config()
        full_config = config.to_dict(safe=False)

        # 应包含完整信息
        assert full_config["DATABASE_URL"] == config.DATABASE_URL
        assert full_config["AI_API_KEY"] == config.AI_API_KEY

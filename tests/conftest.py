# CN5-Lite pytest全局配置和Fixtures
# 提供Mock外部依赖、测试数据等

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from datetime import datetime, timedelta


# ==================
# Mock外部依赖
# ==================

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API响应"""
    with patch('openai.ChatCompletion.create') as mock:
        mock.return_value = Mock(
            choices=[
                Mock(
                    message=Mock(
                        content="""
class MAStrategy:
    def __init__(self):
        self.ma5 = []
        self.ma20 = []

    def on_bar(self, bar):
        self.ma5.append(bar['close'])
        self.ma20.append(bar['close'])

        if len(self.ma5) > 5:
            self.ma5.pop(0)
        if len(self.ma20) > 20:
            self.ma20.pop(0)

        if len(self.ma5) == 5 and len(self.ma20) == 20:
            ma5_avg = sum(self.ma5) / 5
            ma20_avg = sum(self.ma20) / 20

            if ma5_avg > ma20_avg:
                return {'action': 'buy', 'volume': 100}
            elif ma5_avg < ma20_avg:
                return {'action': 'sell', 'volume': 100}
        return None
"""
                    )
                )
            ]
        )
        yield mock


@pytest.fixture
def mock_openai_error():
    """Mock OpenAI API错误"""
    with patch('openai.ChatCompletion.create') as mock:
        mock.side_effect = Exception("API rate limit exceeded")
        yield mock


@pytest.fixture
def mock_akshare_success():
    """Mock AkShare成功返回数据"""
    with patch('akshare.stock_zh_a_hist') as mock:
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        mock.return_value = pd.DataFrame({
            '日期': dates.strftime('%Y-%m-%d').tolist(),
            '开盘': [10.0 + i * 0.1 for i in range(10)],
            '最高': [10.5 + i * 0.1 for i in range(10)],
            '最低': [9.5 + i * 0.1 for i in range(10)],
            '收盘': [10.2 + i * 0.1 for i in range(10)],
            '成交量': [1000000 + i * 10000 for i in range(10)]
        })
        yield mock


@pytest.fixture
def mock_akshare_fail():
    """Mock AkShare失败（用于测试降级）"""
    with patch('akshare.stock_zh_a_hist') as mock:
        mock.side_effect = Exception("Network timeout")
        yield mock


@pytest.fixture
def mock_all_datasources_fail():
    """Mock所有数据源失败"""
    with patch('akshare.stock_zh_a_hist') as mock_ak, \
         patch('baostock.query_history_k_data_plus') as mock_bs, \
         patch('efinance.stock.get_quote_history') as mock_ef:

        mock_ak.side_effect = Exception("AkShare failed")
        mock_bs.side_effect = Exception("Baostock failed")
        mock_ef.side_effect = Exception("Efinance failed")

        yield {'akshare': mock_ak, 'baostock': mock_bs, 'efinance': mock_ef}


# ==================
# Redis Mock
# ==================

@pytest.fixture
def redis_client():
    """使用fakeredis模拟Redis"""
    import fakeredis
    return fakeredis.FakeStrictRedis()


# ==================
# 数据库Mock
# ==================

@pytest.fixture
def db_session():
    """使用SQLite内存数据库进行测试"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # 创建内存数据库
    engine = create_engine('sqlite:///:memory:')

    # TODO: 在实现models后，创建表
    # Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


# ==================
# 测试数据
# ==================

@pytest.fixture
def sample_kline_data():
    """示例K线数据（归一化后格式）"""
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    return pd.DataFrame({
        'date': dates,
        'open': [10.0 + i * 0.1 for i in range(20)],
        'high': [10.5 + i * 0.1 for i in range(20)],
        'low': [9.5 + i * 0.1 for i in range(20)],
        'close': [10.2 + i * 0.1 for i in range(20)],
        'volume': [1000000 + i * 10000 for i in range(20)]
    })


@pytest.fixture
def sample_kline_data_with_halt():
    """包含停牌的K线数据"""
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    data = pd.DataFrame({
        'date': dates,
        'open': [10.0] * 10,
        'high': [10.5] * 10,
        'low': [9.5] * 10,
        'close': [10.2] * 10,
        'volume': [1000000] * 10
    })
    # 第5天停牌
    data.loc[4, 'volume'] = 0
    return data


@pytest.fixture
def sample_kline_data_with_invalid_ohlc():
    """包含非法OHLC的数据"""
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    return pd.DataFrame({
        'date': dates,
        'open': [10.0, 10.0, 10.0, 10.0, 10.0],
        'high': [10.5, 10.5, 9.0, 10.5, 10.5],  # 第3行high < close，非法
        'low': [9.5, 9.5, 9.5, 9.5, 9.5],
        'close': [10.2, 10.2, 10.2, 10.2, 10.2],
        'volume': [1000000] * 5
    })


@pytest.fixture
def sample_strategy_code():
    """示例策略代码（双均线）"""
    return """
class MAStrategy:
    def __init__(self):
        self.ma5 = []
        self.ma20 = []

    def on_bar(self, bar):
        self.ma5.append(bar['close'])
        self.ma20.append(bar['close'])

        if len(self.ma5) > 5:
            self.ma5.pop(0)
        if len(self.ma20) > 20:
            self.ma20.pop(0)

        if len(self.ma5) == 5 and len(self.ma20) == 20:
            ma5_avg = sum(self.ma5) / 5
            ma20_avg = sum(self.ma20) / 20

            if ma5_avg > ma20_avg:
                return {'action': 'buy', 'symbol': '000001.SZ', 'volume': 100}
            elif ma5_avg < ma20_avg:
                return {'action': 'sell', 'symbol': '000001.SZ', 'volume': 100}
        return None
"""


@pytest.fixture
def sample_dangerous_strategy_code():
    """危险策略代码（用于测试安全检查）"""
    return """
class EvilStrategy:
    def on_bar(self, bar):
        import os
        os.system('rm -rf /')  # 危险操作
        return None
"""


@pytest.fixture
def sample_complex_strategy_code():
    """复杂策略代码（用于测试圈复杂度）"""
    # 生成超过20层复杂度的代码
    conditions = "\n        ".join([f"if condition{i}: pass" for i in range(25)])
    return f"""
class ComplexStrategy:
    def on_bar(self, bar):
        {conditions}
        return None
"""


# ==================
# 测试环境配置
# ==================

@pytest.fixture(scope="session")
def test_config():
    """测试环境配置"""
    return {
        'DATABASE_URL': 'sqlite:///:memory:',
        'REDIS_URL': 'redis://localhost:6379/0',
        'AI_API_KEY': 'test-key-12345',
        'AI_MODEL': 'deepseek-chat',
        'INITIAL_CASH': 100000,
        'COMMISSION_RATE': 0.0003,
        'MIN_COMMISSION': 5.0,
        'TAX_RATE': 0.001,
        'SLIPPAGE': 0.001,
    }


# ==================
# Pytest Hooks
# ==================

def pytest_configure(config):
    """pytest配置钩子"""
    config.addinivalue_line(
        "markers", "slow: 慢速测试（真实API调用）"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试"
    )
    config.addinivalue_line(
        "markers", "requires_api_key: 需要AI API密钥"
    )


def pytest_collection_modifyitems(config, items):
    """自动跳过需要API密钥的测试（如果未提供）"""
    import os

    if not os.getenv('AI_API_KEY'):
        skip_api = pytest.mark.skip(reason="需要AI_API_KEY环境变量")
        for item in items:
            if "requires_api_key" in item.keywords:
                item.add_marker(skip_api)

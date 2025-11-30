"""
CN5-Lite 回测引擎测试

测试范围:
1. 基础回测执行
2. 性能指标计算
3. A股市场规则
4. 涨跌停限制
5. T+1制度集成
6. 税费计算
7. 交易单位验证
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestBacktestEngine:
    """回测引擎基础测试"""

    def test_engine_init(self):
        """测试引擎初始化"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(initial_cash=100000)

        assert engine is not None
        assert engine.initial_cash == 100000

    def test_run_simple_backtest(self):
        """测试执行简单回测"""
        from app.services.backtest_engine import BacktestEngine

        # 简单策略：收盘价上涨就买入
        strategy_code = """
class SimpleStrategy:
    def __init__(self):
        self.last_close = None

    def on_bar(self, bar):
        if self.last_close and bar['close'] > self.last_close:
            self.last_close = bar['close']
            return {'action': 'buy', 'symbol': 'SH600000', 'amount': 100}
        self.last_close = bar['close']
        return None
"""

        # 模拟数据
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10, freq='D'),
            'open': [10.0] * 10,
            'high': [10.5] * 10,
            'low': [9.5] * 10,
            'close': [10.0, 10.1, 10.2, 10.1, 10.3, 10.4, 10.3, 10.5, 10.6, 10.7],
            'volume': [1000000] * 10
        })

        engine = BacktestEngine(initial_cash=100000)
        result = engine.run(strategy_code, data, symbol='SH600000')

        assert 'annual_return' in result
        assert 'total_trades' in result

    def test_backtest_returns_metrics(self):
        """测试回测返回完整指标"""
        from app.services.backtest_engine import BacktestEngine

        strategy_code = """
class MetricsStrategy:
    def on_bar(self, bar):
        return None
"""

        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=5, freq='D'),
            'open': [10] * 5,
            'high': [11] * 5,
            'low': [9] * 5,
            'close': [10, 11, 12, 11, 12],
            'volume': [1000000] * 5
        })

        engine = BacktestEngine(initial_cash=100000)
        result = engine.run(strategy_code, data, symbol='SH600000')

        # 验证包含所有关键指标
        assert 'annual_return' in result
        assert 'max_drawdown' in result
        assert 'sharpe_ratio' in result
        assert 'win_rate' in result
        assert 'total_trades' in result
        assert 'final_value' in result


class TestPerformanceMetrics:
    """性能指标计算测试"""

    def test_calculate_annual_return(self):
        """测试年化收益率计算"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(initial_cash=100000)

        # 计算年化收益
        final_value = 120000  # 20%收益
        days = 365
        annual_return = engine._calculate_annual_return(final_value, days)

        assert abs(annual_return - 0.20) < 0.01

    def test_calculate_max_drawdown(self):
        """测试最大回撤计算"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(initial_cash=100000)

        # 模拟账户价值变化
        values = [100000, 110000, 105000, 120000, 100000, 115000]

        max_dd = engine._calculate_max_drawdown(values)

        # 最大回撤：从120000跌到100000 = 16.67%
        assert abs(max_dd - 0.1667) < 0.01

    def test_calculate_sharpe_ratio(self):
        """测试夏普比率计算"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(initial_cash=100000)

        # 模拟每日收益率
        returns = [0.01, -0.005, 0.02, 0.01, -0.01, 0.015]

        sharpe = engine._calculate_sharpe_ratio(returns)

        assert isinstance(sharpe, float)
        assert sharpe > 0  # 正收益应该有正夏普

    def test_calculate_win_rate(self):
        """测试胜率计算"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(initial_cash=100000)

        # 模拟交易记录
        trades = [
            {'profit': 100},
            {'profit': -50},
            {'profit': 200},
            {'profit': 150},
            {'profit': -30}
        ]

        win_rate = engine._calculate_win_rate(trades)

        assert win_rate == 0.6  # 3胜2负 = 60%


class TestChinaMarketRules:
    """A股市场规则测试"""

    def test_detect_suspension(self):
        """测试停牌检测"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        # volume=0表示停牌
        bar = {'date': '2024-01-01', 'close': 10.0, 'volume': 0}

        is_suspended = engine._is_suspended(bar)

        assert is_suspended is True

    def test_normal_trading(self):
        """测试正常交易日"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        bar = {'date': '2024-01-01', 'close': 10.0, 'volume': 1000000}

        is_suspended = engine._is_suspended(bar)

        assert is_suspended is False

    def test_limit_up_detection(self):
        """测试涨停检测"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        # 普通股票涨停：10%
        yesterday_close = 10.0
        today_close = 11.0  # +10%

        is_limit_up = engine._is_limit_up(today_close, yesterday_close, stock_type='normal')

        assert is_limit_up is True

    def test_limit_down_detection(self):
        """测试跌停检测"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        # 普通股票跌停：-10%
        yesterday_close = 10.0
        today_close = 9.0  # -10%

        is_limit_down = engine._is_limit_down(today_close, yesterday_close, stock_type='normal')

        assert is_limit_down is True

    def test_st_stock_limit(self):
        """测试ST股票涨跌停限制（±5%）"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        yesterday_close = 10.0
        today_close = 10.5  # +5%

        is_limit_up = engine._is_limit_up(today_close, yesterday_close, stock_type='st')

        assert is_limit_up is True

    def test_cyb_kcb_limit(self):
        """测试创业板/科创板涨跌停限制（±20%）"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        yesterday_close = 10.0
        today_close = 12.0  # +20%

        is_limit_up = engine._is_limit_up(today_close, yesterday_close, stock_type='cyb')

        assert is_limit_up is True


class TestTradingFees:
    """交易税费测试"""

    def test_buy_commission(self):
        """测试买入佣金"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        # 买入1000股，每股10元
        commission = engine._calculate_commission(10000, is_buy=True)

        # 佣金：10000 * 0.0003 = 3元，但最低5元
        assert commission == 5.0

    def test_sell_commission_and_tax(self):
        """测试卖出佣金和印花税"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        # 卖出10000元
        commission = engine._calculate_commission(10000, is_buy=False)
        tax = engine._calculate_stamp_tax(10000)

        # 佣金：10000 * 0.0003 = 3元，最低5元
        assert commission == 5.0

        # 印花税：10000 * 0.001 = 10元
        assert tax == 10.0

    def test_large_trade_commission(self):
        """测试大额交易佣金"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        # 买入100000元
        commission = engine._calculate_commission(100000, is_buy=True)

        # 佣金：100000 * 0.0003 = 30元
        assert commission == 30.0

    def test_total_trade_cost(self):
        """测试交易总成本"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        # 买入后卖出
        buy_cost = engine._calculate_trade_cost(10000, is_buy=True)
        sell_cost = engine._calculate_trade_cost(10000, is_buy=False)

        # 买入：佣金5元
        assert buy_cost == 5.0

        # 卖出：佣金5元 + 印花税10元 = 15元
        assert sell_cost == 15.0


class TestTradingUnits:
    """交易单位测试"""

    def test_buy_must_be_100_multiple(self):
        """测试买入必须100股整数倍"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        # 验证150股不合法
        is_valid = engine._validate_buy_amount(150)
        assert is_valid is False

        # 验证100股合法
        is_valid = engine._validate_buy_amount(100)
        assert is_valid is True

    def test_sell_can_be_partial(self):
        """测试卖出可以不是100股整数倍（零股）"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True)

        # 卖出50股应该允许
        is_valid = engine._validate_sell_amount(50)
        assert is_valid is True


class TestSlippage:
    """滑点测试"""

    def test_calculate_slippage(self):
        """测试滑点计算"""
        from app.services.backtest_engine import BacktestEngine

        engine = BacktestEngine(enable_china_rules=True, slippage_rate=0.001)

        # 买入：实际成交价 = 价格 * (1 + 滑点)
        actual_price = engine._apply_slippage(10.0, is_buy=True)
        assert actual_price == 10.01

        # 卖出：实际成交价 = 价格 * (1 - 滑点)
        actual_price = engine._apply_slippage(10.0, is_buy=False)
        assert actual_price == 9.99


class TestT1Integration:
    """T+1制度集成测试"""

    def test_t1_lock_from_adapter(self):
        """测试与策略适配器的T+1集成"""
        from app.services.backtest_engine import BacktestEngine

        strategy_code = """
class T1Strategy:
    def __init__(self):
        self.day = 0

    def on_bar(self, bar):
        self.day += 1
        if self.day == 1:
            return {'action': 'buy', 'symbol': 'SH600000', 'amount': 100}
        elif self.day == 2:
            # 尝试当天卖出，应该被T+1拦截
            return {'action': 'sell', 'symbol': 'SH600000', 'amount': 100}
        return None
"""

        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=3, freq='D'),
            'open': [10.0] * 3,
            'high': [10.5] * 3,
            'low': [9.5] * 3,
            'close': [10.0, 10.1, 10.2],
            'volume': [1000000] * 3
        })

        engine = BacktestEngine(initial_cash=100000, enable_china_rules=True)
        result = engine.run(strategy_code, data, symbol='SH600000')

        # 第二天的卖出应该被拦截，只有1笔买入交易
        assert result['total_trades'] == 1


class TestBacktestIntegration:
    """回测集成测试"""

    def test_complete_backtest_flow(self):
        """测试完整回测流程"""
        from app.services.backtest_engine import BacktestEngine

        # 完整策略：MA交叉
        strategy_code = """
class MAStrategy:
    def __init__(self):
        self.prices = []
        self.position = 0

    def on_bar(self, bar):
        self.prices.append(bar['close'])

        if len(self.prices) < 5:
            return None

        # 简单MA5
        ma5 = sum(self.prices[-5:]) / 5

        if bar['close'] > ma5 and self.position == 0:
            self.position = 100
            return {'action': 'buy', 'symbol': 'SH600000', 'amount': 100}
        elif bar['close'] < ma5 and self.position > 0:
            self.position = 0
            return {'action': 'sell', 'symbol': 'SH600000', 'amount': 100}

        return None
"""

        # 30天数据
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30, freq='D'),
            'open': np.random.uniform(9.5, 10.5, 30),
            'high': np.random.uniform(10, 11, 30),
            'low': np.random.uniform(9, 10, 30),
            'close': np.random.uniform(9.5, 10.5, 30),
            'volume': np.random.uniform(800000, 1200000, 30)
        })

        engine = BacktestEngine(initial_cash=100000, enable_china_rules=True)
        result = engine.run(strategy_code, data, symbol='SH600000')

        # 验证结果完整性
        assert result['final_value'] > 0
        assert result['total_trades'] >= 0
        assert 'annual_return' in result
        assert 'max_drawdown' in result

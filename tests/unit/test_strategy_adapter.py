"""
CN5-Lite 策略适配器测试

测试范围:
1. 标准策略解析
2. 策略状态管理
3. 订单信号生成
4. T+1锁定逻辑
5. 技术指标状态
6. 防未来函数
"""

import pytest
from datetime import datetime, timedelta


class TestStandardStrategy:
    """标准策略解析测试"""

    def test_parse_simple_strategy(self):
        """测试解析简单策略"""
        from app.services.strategy_adapter import StandardStrategy

        code = """
class SimpleStrategy:
    def __init__(self):
        self.prices = []

    def on_bar(self, bar):
        self.prices.append(bar['close'])
        return None
"""

        strategy = StandardStrategy(code)

        assert strategy is not None
        assert hasattr(strategy, 'on_bar')

    def test_strategy_on_bar_execution(self):
        """测试on_bar方法执行"""
        from app.services.strategy_adapter import StandardStrategy

        code = """
class TestStrategy:
    def __init__(self):
        self.call_count = 0

    def on_bar(self, bar):
        self.call_count += 1
        return {'action': 'buy', 'amount': 100}
"""

        strategy = StandardStrategy(code)

        # 调用on_bar
        bar = {'date': '2024-01-01', 'close': 10.0, 'open': 9.5}
        signal = strategy.on_bar(bar)

        assert signal['action'] == 'buy'
        assert signal['amount'] == 100

    def test_strategy_state_persistence(self):
        """测试策略状态持久化"""
        from app.services.strategy_adapter import StandardStrategy

        code = """
class StatefulStrategy:
    def __init__(self):
        self.counter = 0
        self.prices = []

    def on_bar(self, bar):
        self.counter += 1
        self.prices.append(bar['close'])
        return {'counter': self.counter, 'avg_price': sum(self.prices) / len(self.prices)}
"""

        strategy = StandardStrategy(code)

        # 第一次调用
        signal1 = strategy.on_bar({'close': 10.0})
        assert signal1['counter'] == 1

        # 第二次调用，状态应该保留
        signal2 = strategy.on_bar({'close': 12.0})
        assert signal2['counter'] == 2
        assert signal2['avg_price'] == 11.0


class TestStrategyAdapter:
    """策略适配器测试"""

    def test_adapter_init(self):
        """测试适配器初始化"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class MyStrategy:
    def on_bar(self, bar):
        return None
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        assert adapter is not None
        assert adapter.strategy_id == 1

    def test_process_bar_without_signal(self):
        """测试处理K线但不产生信号"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class NoSignalStrategy:
    def on_bar(self, bar):
        return None
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        bar = {'date': '2024-01-01', 'close': 10.0}
        order = adapter.process_bar(bar)

        assert order is None

    def test_process_bar_with_buy_signal(self):
        """测试处理K线产生买入信号"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class BuyStrategy:
    def on_bar(self, bar):
        if bar['close'] > 10:
            return {'action': 'buy', 'amount': 100}
        return None
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        bar = {'date': '2024-01-01', 'close': 11.0}
        order = adapter.process_bar(bar)

        assert order is not None
        assert order['action'] == 'buy'
        assert order['amount'] == 100

    def test_process_bar_with_sell_signal(self):
        """测试处理K线产生卖出信号"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class SellStrategy:
    def on_bar(self, bar):
        if bar['close'] < 10:
            return {'action': 'sell', 'amount': 50}
        return None
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        bar = {'date': '2024-01-01', 'close': 9.0}
        order = adapter.process_bar(bar)

        assert order is not None
        assert order['action'] == 'sell'
        assert order['amount'] == 50


class TestT1Locking:
    """T+1锁定测试"""

    def test_buy_locks_position(self):
        """测试买入后锁定仓位"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class T1Strategy:
    def on_bar(self, bar):
        return {'action': 'buy', 'amount': 100, 'symbol': 'SH600000'}
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        bar = {'date': '2024-01-01', 'close': 10.0}
        order = adapter.process_bar(bar)

        # 验证买入后，该股票被锁定
        assert adapter.is_locked('SH600000') is True
        assert adapter.get_locked_amount('SH600000') == 100

    def test_locked_position_cannot_sell_same_day(self):
        """测试当日买入的股票不能卖出"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class T1ViolateStrategy:
    def __init__(self):
        self.bar_count = 0

    def on_bar(self, bar):
        self.bar_count += 1
        if self.bar_count == 1:
            return {'action': 'buy', 'amount': 100, 'symbol': 'SH600000'}
        else:
            return {'action': 'sell', 'amount': 100, 'symbol': 'SH600000'}
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        # 第一次：买入
        bar1 = {'date': '2024-01-01', 'close': 10.0}
        order1 = adapter.process_bar(bar1)
        assert order1['action'] == 'buy'

        # 第二次：同一天卖出应该被拦截
        bar2 = {'date': '2024-01-01', 'close': 11.0}
        order2 = adapter.process_bar(bar2)

        # 应该返回None或被标记为T+1违规
        assert order2 is None or order2.get('blocked_by_t1') is True

    def test_unlock_next_trading_day(self):
        """测试下一个交易日解锁"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class UnlockStrategy:
    def __init__(self):
        self.bar_count = 0

    def on_bar(self, bar):
        self.bar_count += 1
        if self.bar_count == 1:
            return {'action': 'buy', 'amount': 100, 'symbol': 'SH600000'}
        else:
            return {'action': 'sell', 'amount': 100, 'symbol': 'SH600000'}
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        # T日买入
        bar1 = {'date': '2024-01-01', 'close': 10.0}
        adapter.process_bar(bar1)

        # T+1日卖出应该允许
        bar2 = {'date': '2024-01-02', 'close': 11.0}
        order2 = adapter.process_bar(bar2)

        assert order2 is not None
        assert order2['action'] == 'sell'
        assert order2.get('blocked_by_t1') is not True


class TestTechnicalIndicators:
    """技术指标状态测试"""

    def test_ma_indicator_calculation(self):
        """测试移动平均线计算"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class MAStrategy:
    def __init__(self):
        self.prices = []

    def on_bar(self, bar):
        self.prices.append(bar['close'])

        # 计算MA5
        if len(self.prices) >= 5:
            ma5 = sum(self.prices[-5:]) / 5
            if bar['close'] > ma5:
                return {'action': 'buy', 'ma5': ma5}
        return None
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        # 推送5个K线
        prices = [10, 11, 12, 11, 13]
        for i, price in enumerate(prices):
            bar = {'date': f'2024-01-0{i+1}', 'close': price}
            order = adapter.process_bar(bar)

        # 第5个K线应该产生信号
        assert order is not None
        assert order['action'] == 'buy'
        assert order['ma5'] == 11.4  # (10+11+12+11+13)/5

    def test_indicator_state_persistence(self):
        """测试指标状态持久化"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class PersistentMA:
    def __init__(self):
        self.prices = []

    def on_bar(self, bar):
        self.prices.append(bar['close'])
        return {'count': len(self.prices)}
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        # 推送3个K线
        for i in range(3):
            bar = {'date': f'2024-01-0{i+1}', 'close': 10.0 + i}
            order = adapter.process_bar(bar)

        # 验证状态累积
        assert order['count'] == 3

        # 获取状态
        state = adapter.get_state()
        assert 'strategy_state' in state
        assert 'prices' in state['strategy_state']
        assert len(state['strategy_state']['prices']) == 3


class TestPreventLookAheadBias:
    """防未来函数测试"""

    def test_only_current_bar_accessible(self):
        """测试只能访问当前K线"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class CurrentOnlyStrategy:
    def on_bar(self, bar):
        # 只应该能访问当前bar
        return {'close': bar['close'], 'date': bar['date']}
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        bar = {'date': '2024-01-01', 'close': 10.0}
        order = adapter.process_bar(bar)

        assert order['close'] == 10.0
        assert order['date'] == '2024-01-01'

    def test_no_future_data_leakage(self):
        """测试无未来数据泄露"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class NoFutureStrategy:
    def __init__(self):
        self.seen_prices = []

    def on_bar(self, bar):
        self.seen_prices.append(bar['close'])
        # 只能基于历史数据决策
        return {'max_seen': max(self.seen_prices)}
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        prices = [10, 12, 11, 13, 9]
        for i, price in enumerate(prices):
            bar = {'date': f'2024-01-0{i+1}', 'close': price}
            order = adapter.process_bar(bar)

            # 在i=2时，max_seen应该是12，而不是13
            if i == 2:
                assert order['max_seen'] == 12

            # 在i=3时，max_seen应该是13
            if i == 3:
                assert order['max_seen'] == 13


class TestOrderExecution:
    """订单执行测试"""

    def test_order_format_validation(self):
        """测试订单格式验证"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class ValidOrderStrategy:
    def on_bar(self, bar):
        return {
            'action': 'buy',
            'symbol': 'SH600000',
            'amount': 100,
            'price': bar['close']
        }
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        bar = {'date': '2024-01-01', 'close': 10.0}
        order = adapter.process_bar(bar)

        assert 'action' in order
        assert 'symbol' in order
        assert 'amount' in order
        assert order['amount'] > 0

    def test_order_amount_100_multiple(self):
        """测试买入数量必须是100的倍数"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class InvalidAmountStrategy:
    def on_bar(self, bar):
        return {'action': 'buy', 'symbol': 'SH600000', 'amount': 150}
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        bar = {'date': '2024-01-01', 'close': 10.0}

        # 应该抛出验证错误或自动修正
        with pytest.raises(ValueError, match="100的倍数|整数倍"):
            adapter.process_bar(bar)


class TestStateManagement:
    """状态管理测试"""

    def test_save_and_restore_state(self):
        """测试保存和恢复状态"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class StatefulStrategy:
    def __init__(self):
        self.counter = 0
        self.total = 0

    def on_bar(self, bar):
        self.counter += 1
        self.total += bar['close']
        return {'counter': self.counter, 'avg': self.total / self.counter}
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        # 处理一些K线
        for i in range(5):
            bar = {'date': f'2024-01-0{i+1}', 'close': 10.0 + i}
            adapter.process_bar(bar)

        # 保存状态
        state = adapter.get_state()

        # 创建新适配器并恢复状态
        adapter2 = StrategyAdapter(code, strategy_id=1)
        adapter2.restore_state(state)

        # 继续处理，状态应该延续
        bar = {'date': '2024-01-06', 'close': 15.0}
        order = adapter2.process_bar(bar)

        assert order['counter'] == 6  # 5 + 1

    def test_state_includes_t1_locks(self):
        """测试状态包含T+1锁定"""
        from app.services.strategy_adapter import StrategyAdapter

        code = """
class BuyStrategy:
    def on_bar(self, bar):
        return {'action': 'buy', 'symbol': 'SH600000', 'amount': 100}
"""

        adapter = StrategyAdapter(code, strategy_id=1)

        bar = {'date': '2024-01-01', 'close': 10.0}
        adapter.process_bar(bar)

        # 获取状态
        state = adapter.get_state()

        # 状态应该包含T+1锁定信息
        assert 't1_locks' in state
        assert 'SH600000' in state['t1_locks']

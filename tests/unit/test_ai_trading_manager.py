"""
CN5-Lite AI交易管理器测试

测试范围:
1. 启动自动交易
2. 免确认模式（≤3000元）
3. 需确认模式
4. 容器重启断点续传
5. 持仓恢复
6. 技术指标恢复
7. T+1锁定恢复
8. 策略逻辑测试
"""

import pytest
from datetime import datetime, timedelta


class TestAITradingManager:
    """AI交易管理器基础测试"""

    def test_manager_init(self):
        """测试管理器初始化"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager()

        assert manager is not None

    def test_init_with_config(self):
        """测试带配置初始化"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager(
            require_approval=False,
            auto_approve_threshold=3000,
            enable_logic_test=True
        )

        assert manager.require_approval is False
        assert manager.auto_approve_threshold == 3000
        assert manager.enable_logic_test is True


class TestAutoTrading:
    """自动交易测试"""

    def test_start_auto_trading(self):
        """测试启动自动交易"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager()

        # 添加策略
        manager.add_strategy(
            strategy_id=1,
            strategy_code="class TestStrategy:\n    def on_bar(self, bar):\n        return None"
        )

        # 启动
        result = manager.start_auto_trading()

        assert result is True

    def test_stop_auto_trading(self):
        """测试停止自动交易"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager()

        manager.start_auto_trading()
        result = manager.stop_auto_trading()

        assert result is True


class TestApprovalMode:
    """确认模式测试"""

    def test_auto_approve_small_trade(self):
        """测试小额交易自动通过"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager(
            require_approval=False,
            auto_approve_threshold=3000
        )

        # 2000元交易，应该自动通过
        signal = {
            'action': 'buy',
            'symbol': 'SH600000',
            'amount': 200,
            'price': 10.0
        }

        approved = manager.check_approval(signal)

        assert approved is True

    def test_require_approval_large_trade(self):
        """测试大额交易需要确认"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager(
            require_approval=False,
            auto_approve_threshold=3000
        )

        # 5000元交易，超过阈值
        signal = {
            'action': 'buy',
            'symbol': 'SH600000',
            'amount': 500,
            'price': 10.0
        }

        approved = manager.check_approval(signal)

        # 超过阈值应该需要确认
        assert approved is False

    def test_manual_approval_mode(self):
        """测试手动确认模式"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager(require_approval=True)

        # 任何交易都需要确认
        signal = {
            'action': 'buy',
            'symbol': 'SH600000',
            'amount': 100,
            'price': 10.0
        }

        approved = manager.check_approval(signal)

        assert approved is False


class TestCrashRecovery:
    """容器重启断点续传测试"""

    def test_rehydrate_state(self):
        """测试状态恢复"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager()

        strategy_code = """
class RecoveryStrategy:
    def __init__(self):
        self.prices = []

    def on_bar(self, bar):
        self.prices.append(bar['close'])
        return None
"""

        # 添加策略
        manager.add_strategy(strategy_id=1, strategy_code=strategy_code)

        # 模拟容器重启，恢复状态
        result = manager.rehydrate_state(strategy_id=1)

        assert 'positions' in result
        assert 'indicators_restored' in result
        assert 'locked_positions' in result

    def test_restore_positions_from_trades(self):
        """测试从交易记录恢复持仓"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager()

        # 模拟历史交易记录
        trades = [
            {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.0},
            {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.5},
            {'action': 'sell', 'symbol': 'SH600000', 'amount': 50, 'price': 11.0}
        ]

        positions = manager._restore_positions(trades)

        # 买入200股，卖出50股，剩余150股
        assert positions['SH600000']['amount'] == 150

    def test_restore_technical_indicators(self):
        """测试恢复技术指标"""
        from app.services.ai_trading_manager import AITradingManager
        import pandas as pd

        manager = AITradingManager()

        strategy_code = """
class MAStrategy:
    def __init__(self):
        self.prices = []

    def on_bar(self, bar):
        self.prices.append(bar['close'])
        return None
"""

        # 历史数据
        historical_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30, freq='D'),
            'close': [10.0 + i * 0.1 for i in range(30)]
        })

        result = manager._restore_indicators(
            strategy_id=1,
            strategy_code=strategy_code,
            historical_data=historical_data
        )

        assert result['indicators_restored'] is True

    def test_restore_t1_locks(self):
        """测试恢复T+1锁定"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager()

        # 今日买入记录
        today = datetime.now().strftime('%Y-%m-%d')
        today_trades = [
            {'symbol': 'SH600000', 'amount': 100, 'date': today},
            {'symbol': 'SH600001', 'amount': 200, 'date': today}
        ]

        locked = manager._restore_t1_locks(today_trades)

        assert 'SH600000' in locked
        assert locked['SH600000'] == 100
        assert 'SH600001' in locked
        assert locked['SH600001'] == 200


class TestStrategyLogicTest:
    """策略逻辑测试"""

    def test_empty_data_handling(self):
        """测试空数据处理"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager(enable_logic_test=True)

        strategy_code = """
class EmptyDataStrategy:
    def on_bar(self, bar):
        if bar:
            return {'action': 'buy', 'amount': 100}
        return None
"""

        result = manager._run_strategy_logic_test(
            strategy_id=1,
            strategy_code=strategy_code
        )

        assert result['passed'] is True

    def test_extreme_market_handling(self):
        """测试极端行情处理"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager(enable_logic_test=True)

        strategy_code = """
class ExtremeStrategy:
    def on_bar(self, bar):
        # 涨停板
        if bar['close'] >= bar['open'] * 1.1:
            return None
        return {'action': 'buy', 'amount': 100}
"""

        result = manager._run_strategy_logic_test(
            strategy_id=1,
            strategy_code=strategy_code
        )

        assert result['passed'] is True

    def test_nan_value_handling(self):
        """测试NaN值处理"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager(enable_logic_test=True)

        strategy_code = """
import math

class NaNStrategy:
    def on_bar(self, bar):
        if math.isnan(bar.get('close', 0)):
            return None
        return {'action': 'buy', 'amount': 100}
"""

        result = manager._run_strategy_logic_test(
            strategy_id=1,
            strategy_code=strategy_code
        )

        assert result['passed'] is True

    def test_boundary_conditions(self):
        """测试边界条件"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager(enable_logic_test=True)

        strategy_code = """
class BoundaryStrategy:
    def on_bar(self, bar):
        if bar['close'] <= 0:
            return None
        return {'action': 'buy', 'amount': 100}
"""

        result = manager._run_strategy_logic_test(
            strategy_id=1,
            strategy_code=strategy_code
        )

        assert result['passed'] is True


class TestTradeExecution:
    """交易执行测试"""

    def test_execute_trade_with_risk_check(self):
        """测试带风控检查的交易执行"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager()

        signal = {
            'action': 'buy',
            'symbol': 'SH600000',
            'amount': 100,
            'price': 10.0,
            'strategy_id': 1
        }

        result = manager.execute_trade(signal)

        assert 'passed_risk_check' in result

    def test_reject_trade_by_risk(self):
        """测试风控拦截交易"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager()

        # 黑名单股票
        signal = {
            'action': 'buy',
            'symbol': 'ST退市',
            'amount': 100,
            'price': 10.0,
            'strategy_id': 1
        }

        result = manager.execute_trade(signal)

        assert result['passed_risk_check'] is False


class TestStrategyManagement:
    """策略管理测试"""

    def test_add_strategy(self):
        """测试添加策略"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager()

        strategy_code = """
class NewStrategy:
    def on_bar(self, bar):
        return None
"""

        result = manager.add_strategy(
            strategy_id=1,
            strategy_code=strategy_code
        )

        assert result is True

    def test_remove_strategy(self):
        """测试移除策略"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager()

        manager.add_strategy(strategy_id=1, strategy_code="class S:\n    pass")
        result = manager.remove_strategy(strategy_id=1)

        assert result is True

    def test_list_strategies(self):
        """测试列出所有策略"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager()

        # 添加多个策略
        for i in range(3):
            manager.add_strategy(
                strategy_id=i+1,
                strategy_code=f"class S{i}:\n    pass"
            )

        strategies = manager.list_strategies()

        assert len(strategies) == 3


class TestIntegration:
    """集成测试"""

    def test_complete_trading_flow(self):
        """测试完整交易流程"""
        from app.services.ai_trading_manager import AITradingManager

        manager = AITradingManager(
            require_approval=False,
            auto_approve_threshold=3000
        )

        # 1. 添加策略
        strategy_code = """
class FlowStrategy:
    def __init__(self):
        self.count = 0

    def on_bar(self, bar):
        self.count += 1
        if self.count == 5 and bar['close'] > 10:
            return {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': bar['close']}
        return None
"""

        manager.add_strategy(strategy_id=1, strategy_code=strategy_code)

        # 2. 启动自动交易
        manager.start_auto_trading()

        # 3. 模拟K线推送
        for i in range(10):
            bar = {
                'date': f'2024-01-{i+1:02d}',
                'close': 10.0 + i * 0.1,
                'open': 10.0,
                'high': 10.5,
                'low': 9.5,
                'volume': 1000000
            }

            manager.process_bar(strategy_id=1, bar=bar)

        # 4. 停止交易
        manager.stop_auto_trading()

        # 验证执行了交易
        trades = manager.get_trades(strategy_id=1)
        assert len(trades) > 0

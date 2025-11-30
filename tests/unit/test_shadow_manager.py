"""
CN5-Lite 影子账户管理器测试

测试范围:
1. 创建影子账户
2. 多维度评分计算
3. 时间权重（指数衰减）
4. Top N策略筛选
5. 晋升条件判断
6. 历史数据回放
7. 按天分段回测
"""

import pytest
from datetime import datetime, timedelta


class TestShadowManager:
    """影子账户管理器基础测试"""

    def test_manager_init(self):
        """测试管理器初始化"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        assert manager is not None

    def test_create_shadow_account(self):
        """测试创建影子账户"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        account_id = manager.create_shadow_account(
            strategy_id=1,
            initial_cash=100000,
            observation_days=7
        )

        assert isinstance(account_id, int)
        assert account_id > 0

    def test_get_shadow_account(self):
        """测试获取影子账户"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)
        account = manager.get_account(account_id)

        assert account is not None
        assert account['strategy_id'] == 1
        assert account['initial_cash'] == 100000
        assert account['status'] == 'observing'


class TestScoreCalculation:
    """评分计算测试"""

    def test_calculate_score_basic(self):
        """测试基础评分计算"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        # 创建账户并模拟交易
        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)

        # 模拟一些回测数据
        manager.update_account_metrics(account_id, {
            'annual_return': 0.20,      # 20%年化收益
            'sharpe_ratio': 1.5,        # 夏普比率1.5
            'max_drawdown': 0.10,       # 10%最大回撤
            'volatility': 0.15,         # 15%波动率
            'win_rate': 0.60            # 60%胜率
        })

        score = manager.calculate_score(account_id)

        assert isinstance(score, float)
        assert score > 0

    def test_score_weights(self):
        """测试评分权重"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        # 验证权重分配：年化收益30%、夏普25%、回撤20%、波动15%、胜率10%
        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)

        # 完美指标
        manager.update_account_metrics(account_id, {
            'annual_return': 1.0,       # 100%收益
            'sharpe_ratio': 3.0,        # 夏普3.0
            'max_drawdown': 0.05,       # 5%回撤
            'volatility': 0.10,         # 10%波动
            'win_rate': 0.80            # 80%胜率
        })

        score = manager.calculate_score(account_id)

        # 完美指标应该得到高分
        assert score >= 80

    def test_score_normalization(self):
        """测试评分归一化"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)

        manager.update_account_metrics(account_id, {
            'annual_return': 0.30,
            'sharpe_ratio': 2.0,
            'max_drawdown': 0.08,
            'volatility': 0.12,
            'win_rate': 0.65
        })

        score = manager.calculate_score(account_id)

        # 分数应该在0-100之间
        assert 0 <= score <= 100


class TestTimeWeight:
    """时间权重测试"""

    def test_time_decay_factor(self):
        """测试时间衰减因子"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        # 7天半衰期
        # 0天：权重1.0
        # 7天：权重0.5
        # 14天：权重0.25

        weight_0d = manager._calculate_time_weight(days=0)
        weight_7d = manager._calculate_time_weight(days=7)
        weight_14d = manager._calculate_time_weight(days=14)

        assert abs(weight_0d - 1.0) < 0.01
        assert abs(weight_7d - 0.5) < 0.01
        assert abs(weight_14d - 0.25) < 0.01

    def test_recent_data_weighted_more(self):
        """测试近期数据权重更高"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)

        # 添加不同时间的交易记录
        # 7天前：低收益
        manager.add_daily_record(account_id, {
            'date': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            'return': -0.05
        })

        # 今天：高收益
        manager.add_daily_record(account_id, {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'return': 0.10
        })

        # 计算加权平均收益
        weighted_return = manager._calculate_weighted_return(account_id)

        # 今天的高收益权重应该更大
        assert weighted_return > 0


class TestTopStrategies:
    """Top N策略筛选测试"""

    def test_get_top_strategies(self):
        """测试获取Top N策略"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        # 创建多个影子账户
        for i in range(5):
            account_id = manager.create_shadow_account(strategy_id=i+1, initial_cash=100000)

            # 不同的表现
            manager.update_account_metrics(account_id, {
                'annual_return': 0.10 + i * 0.05,
                'sharpe_ratio': 1.0 + i * 0.2,
                'max_drawdown': 0.15 - i * 0.01,
                'volatility': 0.20,
                'win_rate': 0.50 + i * 0.05
            })

        # 获取Top 3
        top_strategies = manager.get_top_strategies(limit=3)

        assert len(top_strategies) == 3
        # 应该按分数降序排列
        assert top_strategies[0]['score'] >= top_strategies[1]['score']
        assert top_strategies[1]['score'] >= top_strategies[2]['score']

    def test_min_score_filter(self):
        """测试最低分数过滤"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        # 创建低分策略
        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)
        manager.update_account_metrics(account_id, {
            'annual_return': 0.05,
            'sharpe_ratio': 0.5,
            'max_drawdown': 0.25,
            'volatility': 0.30,
            'win_rate': 0.40
        })

        # 设置最低分数30
        top_strategies = manager.get_top_strategies(limit=10, min_score=30.0)

        # 低分策略应该被过滤
        for strategy in top_strategies:
            assert strategy['score'] >= 30.0


class TestPromotion:
    """晋升条件测试"""

    def test_promotion_criteria(self):
        """测试晋升条件（得分≥35且观察≥14天）"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)

        # 高分但观察天数不足
        manager.update_account_metrics(account_id, {
            'annual_return': 0.30,
            'sharpe_ratio': 2.0,
            'max_drawdown': 0.08,
            'volatility': 0.12,
            'win_rate': 0.65
        })

        # 观察7天
        manager.update_observation_days(account_id, 7)

        can_promote = manager.check_promotion_eligibility(account_id)

        # 天数不足，不能晋升
        assert can_promote is False

    def test_promotion_success(self):
        """测试成功晋升"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)

        # 高分且观察天数足够
        manager.update_account_metrics(account_id, {
            'annual_return': 0.30,
            'sharpe_ratio': 2.0,
            'max_drawdown': 0.08,
            'volatility': 0.12,
            'win_rate': 0.65
        })

        # 观察14天
        manager.update_observation_days(account_id, 14)

        can_promote = manager.check_promotion_eligibility(account_id)

        # 满足条件，可以晋升
        assert can_promote is True

    def test_promote_to_live(self):
        """测试晋升到实盘"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)

        manager.update_account_metrics(account_id, {
            'annual_return': 0.40,
            'sharpe_ratio': 2.5,
            'max_drawdown': 0.06,
            'volatility': 0.10,
            'win_rate': 0.70
        })

        manager.update_observation_days(account_id, 14)

        # 执行晋升
        result = manager.promote_to_live(account_id)

        assert result is True

        # 验证状态变化
        account = manager.get_account(account_id)
        assert account['status'] == 'promoted'


class TestHistoricalReplay:
    """历史数据回放测试"""

    def test_replay_historical_data(self):
        """测试历史数据回放"""
        from app.services.shadow_manager import ShadowManager
        import pandas as pd

        manager = ShadowManager()

        # 准备历史数据
        historical_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10, freq='D'),
            'close': [10.0, 10.5, 10.3, 10.8, 10.6, 11.0, 10.9, 11.2, 11.1, 11.5]
        })

        strategy_code = """
class ReplayStrategy:
    def on_bar(self, bar):
        return None
"""

        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)

        # 回放数据
        result = manager.replay_historical_data(
            account_id=account_id,
            strategy_code=strategy_code,
            data=historical_data
        )

        assert result is not None
        assert 'final_value' in result


class TestDailySegmentation:
    """按天分段回测测试"""

    def test_daily_backtest(self):
        """测试按天分段回测"""
        from app.services.shadow_manager import ShadowManager
        import pandas as pd

        manager = ShadowManager()

        # 30天数据
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30, freq='D'),
            'close': [10.0 + i * 0.1 for i in range(30)]
        })

        strategy_code = """
class DailyStrategy:
    def on_bar(self, bar):
        return None
"""

        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)

        # 按天分段回测
        daily_results = manager.run_daily_backtest(
            account_id=account_id,
            strategy_code=strategy_code,
            data=data
        )

        assert len(daily_results) == 30
        # 每天都应该有结果
        for day_result in daily_results:
            assert 'date' in day_result
            assert 'value' in day_result


class TestAccountLifecycle:
    """账户生命周期测试"""

    def test_account_status_flow(self):
        """测试账户状态流转"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        # 创建 -> 观察中
        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)
        account = manager.get_account(account_id)
        assert account['status'] == 'observing'

        # 晋升 -> 已晋升
        manager.update_account_metrics(account_id, {
            'annual_return': 0.35,
            'sharpe_ratio': 2.0,
            'max_drawdown': 0.08,
            'volatility': 0.12,
            'win_rate': 0.65
        })
        manager.update_observation_days(account_id, 14)
        manager.promote_to_live(account_id)

        account = manager.get_account(account_id)
        assert account['status'] == 'promoted'

    def test_account_termination(self):
        """测试账户终止"""
        from app.services.shadow_manager import ShadowManager

        manager = ShadowManager()

        account_id = manager.create_shadow_account(strategy_id=1, initial_cash=100000)

        # 表现不佳，终止
        manager.update_account_metrics(account_id, {
            'annual_return': -0.20,  # 亏损20%
            'sharpe_ratio': -0.5,
            'max_drawdown': 0.30,
            'volatility': 0.40,
            'win_rate': 0.30
        })

        manager.terminate_account(account_id, reason='表现不佳')

        account = manager.get_account(account_id)
        assert account['status'] == 'terminated'

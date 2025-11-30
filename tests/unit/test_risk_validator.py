"""
CN5-Lite 风控验证器测试

测试范围:
1. 总资金止损（10%）
2. 黑名单股票（ST等）
3. 单日亏损限制（5%）
4. 单策略资金占用（30%）
5. 单笔过大（20%）
6. 异常交易频率（20笔/小时）
7. 涨跌停板检测
"""

import pytest
from datetime import datetime, timedelta


class TestRiskValidator:
    """风控验证器基础测试"""

    def test_validator_init(self):
        """测试验证器初始化"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_total_loss_rate=0.10,
            max_daily_loss_rate=0.05,
            max_strategy_capital_rate=0.30,
            max_single_trade_rate=0.20
        )

        assert validator is not None
        assert validator.total_capital == 100000

    def test_validate_returns_dict(self):
        """测试验证返回字典格式"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        signal = {
            'action': 'buy',
            'symbol': 'SH600000',
            'amount': 100,
            'price': 10.0
        }

        result = validator.validate(signal)

        assert isinstance(result, dict)
        assert 'passed' in result
        assert 'reason' in result
        assert 'risk_score' in result


class TestTotalCapitalStopLoss:
    """总资金止损测试（第1层）"""

    def test_total_loss_within_limit(self):
        """测试总亏损在限制内"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_total_loss_rate=0.10  # 10%止损
        )

        # 当前账户价值95000，亏损5%，在限制内
        validator.update_account_value(95000)

        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is True

    def test_total_loss_exceeds_limit(self):
        """测试总亏损超过限制"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_total_loss_rate=0.10  # 10%止损
        )

        # 当前账户价值88000，亏损12%，超过限制
        validator.update_account_value(88000)

        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is False
        assert '总资金止损' in result['reason'] or '止损' in result['reason']


class TestBlacklist:
    """黑名单股票测试（第2层）"""

    def test_normal_stock_allowed(self):
        """测试正常股票允许交易"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is True

    def test_st_stock_blocked(self):
        """测试ST股票被拦截"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        signal = {'action': 'buy', 'symbol': 'ST退市', 'amount': 100, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is False
        assert '黑名单' in result['reason'] or 'ST' in result['reason']

    def test_custom_blacklist(self):
        """测试自定义黑名单"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            blacklist=['SH600000', 'SZ000001']
        )

        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is False
        assert '黑名单' in result['reason']


class TestDailyLossLimit:
    """单日亏损限制测试（第3层）"""

    def test_daily_loss_within_limit(self):
        """测试单日亏损在限制内"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_daily_loss_rate=0.05  # 5%
        )

        # 今日开始价值100000，当前97000，亏损3%
        validator.update_daily_start_value(100000)
        validator.update_account_value(97000)

        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is True

    def test_daily_loss_exceeds_limit(self):
        """测试单日亏损超过限制"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_daily_loss_rate=0.05  # 5%
        )

        # 今日开始价值100000，当前94000，亏损6%
        validator.update_daily_start_value(100000)
        validator.update_account_value(94000)

        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is False
        assert '单日亏损' in result['reason'] or '日内' in result['reason']


class TestStrategyCapitalLimit:
    """单策略资金占用限制测试（第4层）"""

    def test_strategy_capital_within_limit(self):
        """测试单策略资金占用在限制内"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_strategy_capital_rate=0.30  # 30%
        )

        # 策略1已占用20000（20%），本次买入10000（10%），总30%
        validator.update_strategy_capital(strategy_id=1, capital=20000)

        signal = {
            'action': 'buy',
            'symbol': 'SH600000',
            'amount': 1000,
            'price': 10.0,
            'strategy_id': 1
        }
        result = validator.validate(signal)

        assert result['passed'] is True

    def test_strategy_capital_exceeds_limit(self):
        """测试单策略资金占用超过限制"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_strategy_capital_rate=0.30  # 30%
        )

        # 策略1已占用25000（25%），本次买入10000（10%），总35%超限
        validator.update_strategy_capital(strategy_id=1, capital=25000)

        signal = {
            'action': 'buy',
            'symbol': 'SH600000',
            'amount': 1000,
            'price': 10.0,
            'strategy_id': 1
        }
        result = validator.validate(signal)

        assert result['passed'] is False
        assert '单策略' in result['reason'] or '资金占用' in result['reason']


class TestSingleTradeLimit:
    """单笔过大限制测试（第5层）"""

    def test_single_trade_within_limit(self):
        """测试单笔交易在限制内"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_single_trade_rate=0.20  # 20%
        )

        # 买入15000元（15%），在限制内
        signal = {
            'action': 'buy',
            'symbol': 'SH600000',
            'amount': 1500,
            'price': 10.0
        }
        result = validator.validate(signal)

        assert result['passed'] is True

    def test_single_trade_exceeds_limit(self):
        """测试单笔交易过大"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_single_trade_rate=0.20  # 20%
        )

        # 买入25000元（25%），超过限制
        signal = {
            'action': 'buy',
            'symbol': 'SH600000',
            'amount': 2500,
            'price': 10.0
        }
        result = validator.validate(signal)

        assert result['passed'] is False
        assert '单笔' in result['reason'] or '过大' in result['reason']


class TestTradingFrequency:
    """交易频率限制测试（第6层）"""

    def test_trading_frequency_normal(self):
        """测试正常交易频率"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_trades_per_hour=20
        )

        # 1小时内10笔交易，正常
        now = datetime.now()
        for i in range(10):
            validator.record_trade(now - timedelta(minutes=i*5))

        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is True

    def test_trading_frequency_exceeds(self):
        """测试交易频率过高"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_trades_per_hour=20
        )

        # 1小时内21笔交易，超过限制
        now = datetime.now()
        for i in range(21):
            validator.record_trade(now - timedelta(minutes=i*2))

        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is False
        assert '频率' in result['reason'] or '过高' in result['reason']


class TestLimitPriceCheck:
    """涨跌停板检测测试（第7层）"""

    def test_normal_price_allowed(self):
        """测试正常价格允许交易"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        # 昨收10元，今天10.5元，涨5%正常
        validator.update_prev_close('SH600000', 10.0)

        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.5}
        result = validator.validate(signal)

        assert result['passed'] is True

    def test_limit_up_blocked(self):
        """测试涨停板被拦截"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        # 昨收10元，今天11元，涨停
        validator.update_prev_close('SH600000', 10.0)

        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 11.0}
        result = validator.validate(signal)

        assert result['passed'] is False
        assert '涨停' in result['reason']

    def test_limit_down_blocked(self):
        """测试跌停板被拦截"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        # 昨收10元，今天9元，跌停
        validator.update_prev_close('SH600000', 10.0)

        signal = {'action': 'sell', 'symbol': 'SH600000', 'amount': 100, 'price': 9.0}
        result = validator.validate(signal)

        assert result['passed'] is False
        assert '跌停' in result['reason']


class TestRiskScore:
    """风险评分测试"""

    def test_low_risk_score(self):
        """测试低风险评分"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        # 小额正常交易
        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is True
        assert result['risk_score'] < 30  # 低风险

    def test_medium_risk_score(self):
        """测试中等风险评分"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        # 中等金额交易（15%）
        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 1500, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is True
        assert 30 <= result['risk_score'] < 70  # 中等风险

    def test_high_risk_score(self):
        """测试高风险评分"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        # 大额交易（19%，接近上限）
        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 1900, 'price': 10.0}
        result = validator.validate(signal)

        assert result['passed'] is True
        assert result['risk_score'] >= 70  # 高风险


class TestMultiLayerValidation:
    """多层风控联合测试"""

    def test_all_layers_pass(self):
        """测试所有层级都通过"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        # 设置正常状态
        validator.update_account_value(100000)
        validator.update_daily_start_value(100000)
        validator.update_prev_close('SH600000', 10.0)

        signal = {'action': 'buy', 'symbol': 'SH600000', 'amount': 100, 'price': 10.5, 'strategy_id': 1}
        result = validator.validate(signal)

        assert result['passed'] is True

    def test_multiple_layers_fail(self):
        """测试多层同时失败"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_single_trade_rate=0.20
        )

        # 触发多个风控：单笔过大 + 涨停
        validator.update_prev_close('SH600000', 10.0)

        signal = {
            'action': 'buy',
            'symbol': 'SH600000',
            'amount': 3000,  # 30000元，30%过大
            'price': 11.0     # 涨停
        }
        result = validator.validate(signal)

        assert result['passed'] is False
        # 应该包含至少一个失败原因
        assert len(result['reason']) > 0

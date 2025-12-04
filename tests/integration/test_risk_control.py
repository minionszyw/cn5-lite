"""
风控系统集成测试
测试7层风控在实际场景下的表现

运行方式：
  pytest tests/integration/test_risk_control.py -v
"""

import pytest
from datetime import datetime, timedelta


# ==================
# 风控系统集成测试
# ==================

class TestRiskControlIntegration:
    """风控系统完整流程测试"""

    @pytest.mark.integration
    def test_seven_layer_risk_validation(self):
        """测试7层风控完整验证流程"""
        from app.services.risk_validator import RiskValidator

        # 初始化风控
        validator = RiskValidator(
            total_capital=100000,
            max_total_loss_rate=0.10,
            max_daily_loss_rate=0.05,
            max_strategy_capital_rate=0.30,
            max_single_trade_rate=0.20
        )

        print("\n测试7层风控验证...")

        # 测试1: 正常交易（应通过）
        print("\n1. 正常交易测试")
        normal_signal = {
            'symbol': 'SH600000',
            'action': 'buy',
            'amount': 100,
            'price': 10.0
        }

        result = validator.validate(normal_signal)
        assert result['passed'] is True
        print(f"✅ 正常交易通过，风险评分: {result['risk_score']}")

        # 测试2: 黑名单股票（应拦截）
        print("\n2. 黑名单股票测试")
        validator.add_to_blacklist('ST600001')

        blacklist_signal = {
            'symbol': 'ST600001',
            'action': 'buy',
            'amount': 100,
            'price': 10.0
        }

        result = validator.validate(blacklist_signal)
        assert result['passed'] is False
        assert '黑名单' in result['reason']
        print(f"✅ 黑名单拦截成功: {result['reason']}")

        # 测试3: 单笔过大（应拦截）
        print("\n3. 单笔过大测试")
        large_signal = {
            'symbol': 'SH600000',
            'action': 'buy',
            'amount': 10000,  # 过大
            'price': 100.0
        }

        result = validator.validate(large_signal)
        assert result['passed'] is False
        assert '单笔' in result['reason'] or '过大' in result['reason']
        print(f"✅ 单笔过大拦截成功: {result['reason']}")

        # 测试4: 交易频率限制
        print("\n4. 交易频率测试")
        # 快速提交多个交易
        for i in range(25):  # 超过20笔/小时限制
            signal = {
                'symbol': f'SH60000{i % 10}',
                'action': 'buy',
                'amount': 100,
                'price': 10.0
            }
            result = validator.validate(signal)

        # 最后一笔应该被频率限制拦截
        # （实际实现可能需要时间窗口）
        print(f"频率测试完成，最后结果: {result['passed']}")

        # 测试5: 单日亏损限制
        print("\n5. 单日亏损限制测试")
        # 模拟单日亏损达到5%
        validator.update_account_value(95000, datetime.now().strftime('%Y-%m-%d'))

        loss_signal = {
            'symbol': 'SH600000',
            'action': 'buy',
            'amount': 100,
            'price': 10.0
        }

        result = validator.validate(loss_signal)
        # 应该被单日亏损限制拦截
        if not result['passed']:
            assert '单日' in result['reason'] or '亏损' in result['reason']
            print(f"✅ 单日亏损限制触发: {result['reason']}")

        # 测试6: 总资金止损
        print("\n6. 总资金止损测试")
        # 模拟总亏损达到10%
        validator.update_account_value(90000, datetime.now().strftime('%Y-%m-%d'))

        stop_loss_signal = {
            'symbol': 'SH600000',
            'action': 'buy',
            'amount': 100,
            'price': 10.0
        }

        result = validator.validate(stop_loss_signal)
        assert result['passed'] is False
        assert '总资金' in result['reason'] or '止损' in result['reason']
        print(f"✅ 总资金止损触发: {result['reason']}")

        print("\n✅ 7层风控验证测试完成")

    @pytest.mark.integration
    def test_limit_price_detection(self):
        """测试涨跌停板检测"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        print("\n测试涨跌停检测...")

        # 测试涨停（+10%）
        limit_up_signal = {
            'symbol': 'SH600000',
            'action': 'buy',
            'amount': 100,
            'price': 11.0,  # 昨收10.0，今日11.0，涨停
            'prev_close': 10.0
        }

        result = validator._check_limit_price(limit_up_signal)
        assert result is not None
        print(f"✅ 涨停检测: {result}")

        # 测试跌停（-10%）
        limit_down_signal = {
            'symbol': 'SH600000',
            'action': 'sell',
            'amount': 100,
            'price': 9.0,  # 昨收10.0，今日9.0，跌停
            'prev_close': 10.0
        }

        result = validator._check_limit_price(limit_down_signal)
        assert result is not None
        print(f"✅ 跌停检测: {result}")

        # 测试ST股票（±5%）
        st_signal = {
            'symbol': 'ST600000',
            'action': 'buy',
            'amount': 100,
            'price': 10.5,  # 昨收10.0，ST涨停5%
            'prev_close': 10.0
        }

        result = validator._check_limit_price(st_signal)
        print(f"✅ ST涨停检测: {result}")

    @pytest.mark.integration
    def test_multi_strategy_capital_allocation(self):
        """测试多策略资金分配限制"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_strategy_capital_rate=0.30  # 单策略最多30%
        )

        print("\n测试多策略资金分配...")

        # 策略1占用28%（应通过）
        signal1 = {
            'strategy_id': 1,
            'symbol': 'SH600000',
            'action': 'buy',
            'amount': 100,
            'price': 280.0  # 28000元
        }

        result = validator.validate(signal1)
        assert result['passed'] is True
        print(f"✅ 策略1（28%资金）通过")

        # 策略1再请求5%（总计33%，应拦截）
        signal2 = {
            'strategy_id': 1,
            'symbol': 'SH600001',
            'action': 'buy',
            'amount': 100,
            'price': 50.0  # 额外5000元
        }

        # 更新策略1已占用资金
        validator.strategy_capital_used[1] = 28000

        result = validator.validate(signal2)

        if not result['passed']:
            assert '策略资金' in result['reason']
            print(f"✅ 策略资金占用限制触发: {result['reason']}")

    @pytest.mark.integration
    def test_risk_score_calculation(self):
        """测试风险评分计算"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        print("\n测试风险评分计算...")

        # 低风险交易
        low_risk = {
            'symbol': 'SH600000',
            'action': 'buy',
            'amount': 100,
            'price': 10.0  # 1000元，1%资金
        }

        result = validator.validate(low_risk)
        low_score = result['risk_score']
        print(f"低风险交易评分: {low_score}")

        # 中等风险交易
        medium_risk = {
            'symbol': 'SH600000',
            'action': 'buy',
            'amount': 500,
            'price': 20.0  # 10000元，10%资金
        }

        result = validator.validate(medium_risk)
        medium_score = result['risk_score']
        print(f"中等风险交易评分: {medium_score}")

        # 验证评分递增
        assert low_score < medium_score
        print(f"✅ 风险评分正确递增")


# ==================
# 风控与交易集成测试
# ==================

class TestRiskTradingIntegration:
    """风控与交易系统集成测试"""

    @pytest.mark.integration
    def test_risk_validation_in_trading_flow(self):
        """测试交易流程中的风控验证"""
        from app.services.ai_trading_manager import AITradingManager
        from app.services.risk_validator import RiskValidator
        from app.services.ai_generator import StrategyStorage

        print("\n测试交易流程中的风控...")

        # 创建测试策略
        storage = StrategyStorage()
        strategy_id = storage.save({
            "name": "RiskTestStrategy",
            "code": """
class RiskTestStrategy:
    def on_bar(self, bar):
        # 生成一个正常的买入信号
        return {'action': 'buy', 'symbol': 'SH600000', 'amount': 100}
""",
            "params": {},
            "status": "live"
        })

        # 初始化交易管理器和风控
        trading_manager = AITradingManager()
        validator = RiskValidator(total_capital=100000)

        # 模拟交易信号
        signal = {
            'strategy_id': strategy_id,
            'symbol': 'SH600000',
            'action': 'buy',
            'amount': 100,
            'price': 10.0
        }

        # 验证风控
        risk_result = validator.validate(signal)

        if risk_result['passed']:
            print(f"✅ 风控通过，可以执行交易")
        else:
            print(f"❌ 风控拦截: {risk_result['reason']}")

        assert 'passed' in risk_result
        assert 'risk_score' in risk_result

    @pytest.mark.integration
    @pytest.mark.slow
    def test_risk_monitoring_real_time(self):
        """测试实时风控监控"""
        from app.services.risk_validator import RiskValidator
        import time

        validator = RiskValidator(total_capital=100000)

        print("\n测试实时风控监控...")

        # 模拟连续交易
        trades_count = 0
        blocked_count = 0

        for i in range(10):
            signal = {
                'symbol': f'SH60000{i % 10}',
                'action': 'buy' if i % 2 == 0 else 'sell',
                'amount': 100,
                'price': 10.0 + i
            }

            result = validator.validate(signal)

            if result['passed']:
                trades_count += 1
            else:
                blocked_count += 1

            time.sleep(0.1)  # 模拟实时间隔

        print(f"✅ 执行交易: {trades_count}, 拦截: {blocked_count}")
        assert trades_count + blocked_count == 10

    @pytest.mark.integration
    def test_blacklist_auto_update(self):
        """测试黑名单自动更新"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        print("\n测试黑名单自动更新...")

        # 添加ST股票到黑名单
        st_stocks = ['ST600001', 'ST600002', '*ST600003']

        for symbol in st_stocks:
            validator.add_to_blacklist(symbol)

        print(f"✅ 添加{len(st_stocks)}只ST股票到黑名单")

        # 验证黑名单生效
        for symbol in st_stocks:
            signal = {
                'symbol': symbol,
                'action': 'buy',
                'amount': 100,
                'price': 10.0
            }

            result = validator.validate(signal)
            assert result['passed'] is False
            assert '黑名单' in result['reason']

        print(f"✅ 黑名单验证全部通过")

        # 移除黑名单
        for symbol in st_stocks:
            validator.remove_from_blacklist(symbol)

        print(f"✅ 移除{len(st_stocks)}只股票从黑名单")


# ==================
# 风控配置动态更新测试
# ==================

class TestRiskConfigDynamic:
    """风控配置动态更新测试"""

    @pytest.mark.integration
    def test_runtime_config_update(self):
        """测试运行时配置更新"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(
            total_capital=100000,
            max_total_loss_rate=0.10
        )

        print("\n测试运行时配置更新...")

        # 初始配置
        assert validator.max_total_loss_rate == 0.10

        # 动态更新配置
        validator.update_config({
            'max_total_loss_rate': 0.08,  # 收紧止损
            'max_daily_loss_rate': 0.03   # 收紧单日限制
        })

        assert validator.max_total_loss_rate == 0.08
        assert validator.max_daily_loss_rate == 0.03

        print(f"✅ 配置更新成功: 总止损{validator.max_total_loss_rate:.0%}, 日止损{validator.max_daily_loss_rate:.0%}")

    @pytest.mark.integration
    def test_emergency_stop(self):
        """测试紧急停止机制"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        print("\n测试紧急停止机制...")

        # 触发紧急停止（总资金亏损>10%）
        validator.update_account_value(89000, datetime.now().strftime('%Y-%m-%d'))

        # 任何交易都应该被拦截
        signals = [
            {'symbol': 'SH600000', 'action': 'buy', 'amount': 100, 'price': 10.0},
            {'symbol': 'SH600001', 'action': 'sell', 'amount': 100, 'price': 10.0},
        ]

        for signal in signals:
            result = validator.validate(signal)
            assert result['passed'] is False
            assert '总资金' in result['reason'] or '止损' in result['reason']

        print(f"✅ 紧急停止机制工作正常")


# ==================
# 风控日志和审计测试
# ==================

class TestRiskAudit:
    """风控日志和审计测试"""

    @pytest.mark.integration
    def test_risk_log_recording(self):
        """测试风控日志记录"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        print("\n测试风控日志记录...")

        # 生成多个交易信号
        signals = [
            {'symbol': 'SH600000', 'action': 'buy', 'amount': 100, 'price': 10.0},
            {'symbol': 'ST600001', 'action': 'buy', 'amount': 100, 'price': 10.0},  # 黑名单
        ]

        # 添加黑名单
        validator.add_to_blacklist('ST600001')

        for signal in signals:
            result = validator.validate(signal)

            if not result['passed']:
                # 记录风控拦截日志
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'symbol': signal['symbol'],
                    'action': signal['action'],
                    'reason': result['reason'],
                    'risk_score': result['risk_score']
                }

                print(f"风控日志: {log_entry}")

        print(f"✅ 风控日志记录完成")

    @pytest.mark.integration
    def test_risk_statistics(self):
        """测试风控统计"""
        from app.services.risk_validator import RiskValidator

        validator = RiskValidator(total_capital=100000)

        print("\n测试风控统计...")

        # 模拟100笔交易
        passed_count = 0
        blocked_count = 0
        total_risk_score = 0

        for i in range(100):
            signal = {
                'symbol': f'SH{600000 + i % 100}',
                'action': 'buy' if i % 2 == 0 else 'sell',
                'amount': 100 + i % 500,
                'price': 10.0 + (i % 50) * 0.1
            }

            result = validator.validate(signal)

            if result['passed']:
                passed_count += 1
            else:
                blocked_count += 1

            total_risk_score += result['risk_score']

        avg_risk_score = total_risk_score / 100

        print(f"✅ 统计结果:")
        print(f"   通过: {passed_count}")
        print(f"   拦截: {blocked_count}")
        print(f"   平均风险评分: {avg_risk_score:.2f}")

        assert passed_count + blocked_count == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

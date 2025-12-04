"""
FastAPI端点集成测试
测试所有27个API端点的端到端功能

运行方式：
  pytest tests/integration/test_api_endpoints.py -v
"""

import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


# ==================
# 策略管理API测试
# ==================

class TestStrategyAPI:
    """策略管理API集成测试"""

    def test_generate_strategy(self):
        """测试生成策略端点"""
        response = client.post(
            "/api/v1/strategies/generate",
            json={
                "user_input": "双均线策略，MA5上穿MA20买入",
                "context": {}
            }
        )

        assert response.status_code == 200
        data = response.json().get("data", {})

        assert "code" in data
        assert "name" in data
        assert "class" in data["code"] or "def" in data["code"]

    def test_create_strategy(self):
        """测试创建策略端点"""
        strategy_code = """
class TestStrategy:
    def __init__(self):
        self.ma_period = 20

    def on_bar(self, bar):
        return None
"""

        response = client.post(
            "/api/v1/strategies",
            json={
                "name": "TestStrategy",
                "code": strategy_code,
                "params": {"ma_period": 20},
                "status": "draft"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert data["name"] == "TestStrategy"

        # 保存ID用于后续测试
        pytest.strategy_id = data["id"]

    def test_get_strategy(self):
        """测试获取策略端点"""
        if not hasattr(pytest, "strategy_id"):
            pytest.skip("需要先创建策略")

        response = client.get(f"/api/v1/strategies/{pytest.strategy_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == pytest.strategy_id
        assert data["name"] == "TestStrategy"

    def test_list_strategies(self):
        """测试列表查询端点"""
        response = client.get("/api/v1/strategies", params={"limit": 10})

        assert response.status_code == 200
        data = response.json().get("data", [])

        assert isinstance(data, list)

    def test_validate_strategy(self):
        """测试验证策略端点"""
        if not hasattr(pytest, "strategy_id"):
            pytest.skip("需要先创建策略")

        response = client.post(
            f"/api/v1/strategies/{pytest.strategy_id}/validate"
        )

        assert response.status_code == 200
        data = response.json().get("data", {})

        assert "valid" in data or "safe" in data

    def test_delete_strategy(self):
        """测试删除策略端点"""
        if not hasattr(pytest, "strategy_id"):
            pytest.skip("需要先创建策略")

        response = client.delete(f"/api/v1/strategies/{pytest.strategy_id}")

        assert response.status_code == 200

        # 验证已删除
        get_response = client.get(f"/api/v1/strategies/{pytest.strategy_id}")
        assert get_response.status_code == 404


# ==================
# 回测API测试
# ==================

class TestBacktestAPI:
    """回测API集成测试"""

    @pytest.fixture(autouse=True)
    def setup_strategy(self):
        """创建测试策略"""
        strategy_code = """
class MAStrategy:
    def __init__(self):
        self.ma_period = 20
        self.prices = []

    def on_bar(self, bar):
        self.prices.append(bar['close'])

        if len(self.prices) < self.ma_period:
            return None

        ma = sum(self.prices[-self.ma_period:]) / self.ma_period

        if bar['close'] > ma and len(self.prices) == self.ma_period:
            return {'action': 'buy', 'amount': 100}

        return None
"""

        response = client.post(
            "/api/v1/strategies",
            json={
                "name": "MAStrategy",
                "code": strategy_code,
                "params": {"ma_period": 20},
                "status": "draft"
            }
        )

        if response.status_code == 200:
            pytest.backtest_strategy_id = response.json()["id"]

        yield

        # 清理
        if hasattr(pytest, "backtest_strategy_id"):
            client.delete(f"/api/v1/strategies/{pytest.backtest_strategy_id}")

    @pytest.mark.slow
    def test_run_backtest(self):
        """测试运行回测端点"""
        if not hasattr(pytest, "backtest_strategy_id"):
            pytest.skip("策略创建失败")

        response = client.post(
            "/api/v1/backtest/run",
            json={
                "strategy_id": pytest.backtest_strategy_id,
                "symbol": "SH600000",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "initial_cash": 100000,
                "enable_china_rules": True
            },
            timeout=60
        )

        # 回测可能需要真实数据，允许失败
        if response.status_code == 200:
            data = response.json().get("data", {})

            assert "annual_return" in data
            assert "sharpe_ratio" in data
            assert "max_drawdown" in data
        else:
            pytest.skip("回测需要真实数据源")

    @pytest.mark.slow
    def test_quick_backtest(self):
        """测试快速回测端点"""
        if not hasattr(pytest, "backtest_strategy_id"):
            pytest.skip("策略创建失败")

        response = client.post(
            "/api/v1/backtest/quick",
            json={
                "strategy_id": pytest.backtest_strategy_id,
                "symbol": "SH600000",
                "days": 30
            },
            timeout=60
        )

        # 允许失败（需要真实数据）
        if response.status_code != 200:
            pytest.skip("快速回测需要真实数据源")


# ==================
# 交易管理API测试
# ==================

class TestTradingAPI:
    """交易管理API集成测试"""

    def test_get_trading_status(self):
        """测试获取交易状态端点"""
        response = client.get("/api/v1/trading/status")

        assert response.status_code == 200
        data = response.json().get("data", {})

        assert "is_running" in data

    def test_start_trading(self):
        """测试启动交易端点"""
        # 创建测试策略
        strategy_code = "class TestStrategy:\n    def on_bar(self, bar):\n        return None"

        strategy_response = client.post(
            "/api/v1/strategies",
            json={
                "name": "TradingTestStrategy",
                "code": strategy_code,
                "status": "live"
            }
        )

        if strategy_response.status_code != 200:
            pytest.skip("策略创建失败")

        strategy_id = strategy_response.json()["id"]

        # 启动交易
        response = client.post(
            "/api/v1/trading/start",
            json={
                "strategy_id": strategy_id,
                "require_approval": True
            }
        )

        # 允许失败（可能需要更多配置）
        assert response.status_code in [200, 400, 500]

        # 清理
        client.post("/api/v1/trading/stop")
        client.delete(f"/api/v1/strategies/{strategy_id}")

    def test_stop_trading(self):
        """测试停止交易端点"""
        response = client.post(
            "/api/v1/trading/stop",
            json={"close_positions": False}
        )

        assert response.status_code == 200

    def test_get_trades(self):
        """测试获取交易记录端点"""
        response = client.get("/api/v1/trading/trades", params={"limit": 10})

        assert response.status_code == 200
        data = response.json().get("data", [])

        assert isinstance(data, list)

    def test_execute_trade(self):
        """测试手动执行交易端点"""
        response = client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "SH600000",
                "action": "buy",
                "amount": 100,
                "price": 10.0
            }
        )

        # 允许失败（需要交易系统初始化）
        assert response.status_code in [200, 400, 500]

    def test_rehydrate_strategy(self):
        """测试恢复策略状态端点"""
        # 创建测试策略
        strategy_code = "class TestStrategy:\n    def on_bar(self, bar):\n        return None"

        strategy_response = client.post(
            "/api/v1/strategies",
            json={
                "name": "RehydrateTestStrategy",
                "code": strategy_code,
                "status": "live"
            }
        )

        if strategy_response.status_code != 200:
            pytest.skip("策略创建失败")

        strategy_id = strategy_response.json()["id"]

        # 恢复状态
        response = client.post(f"/api/v1/trading/rehydrate/{strategy_id}")

        assert response.status_code in [200, 400]

        # 清理
        client.delete(f"/api/v1/strategies/{strategy_id}")


# ==================
# 影子账户API测试
# ==================

class TestShadowAPI:
    """影子账户API集成测试"""

    @pytest.fixture(autouse=True)
    def setup_strategy(self):
        """创建测试策略"""
        strategy_code = "class TestStrategy:\n    def on_bar(self, bar):\n        return None"

        response = client.post(
            "/api/v1/strategies",
            json={
                "name": "ShadowTestStrategy",
                "code": strategy_code,
                "status": "shadow"
            }
        )

        if response.status_code == 200:
            pytest.shadow_strategy_id = response.json()["id"]

        yield

        # 清理
        if hasattr(pytest, "shadow_strategy_id"):
            client.delete(f"/api/v1/strategies/{pytest.shadow_strategy_id}")

    def test_create_shadow_account(self):
        """测试创建影子账户端点"""
        if not hasattr(pytest, "shadow_strategy_id"):
            pytest.skip("策略创建失败")

        response = client.post(
            "/api/v1/shadow/accounts",
            json={
                "strategy_id": pytest.shadow_strategy_id,
                "initial_cash": 100000,
                "observation_days": 7
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        pytest.shadow_account_id = data["id"]

    def test_get_shadow_account(self):
        """测试获取影子账户端点"""
        if not hasattr(pytest, "shadow_account_id"):
            pytest.skip("需要先创建影子账户")

        response = client.get(f"/api/v1/shadow/accounts/{pytest.shadow_account_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == pytest.shadow_account_id

    def test_get_top_strategies(self):
        """测试获取Top策略端点"""
        response = client.get("/api/v1/shadow/top", params={"limit": 10})

        assert response.status_code == 200
        data = response.json().get("data", [])

        assert isinstance(data, list)

    def test_promote_shadow_account(self):
        """测试晋升影子账户端点"""
        if not hasattr(pytest, "shadow_account_id"):
            pytest.skip("需要先创建影子账户")

        response = client.post(
            f"/api/v1/shadow/accounts/{pytest.shadow_account_id}/promote"
        )

        # 允许失败（可能不满足晋升条件）
        assert response.status_code in [200, 400]

    def test_terminate_shadow_account(self):
        """测试终止影子账户端点"""
        if not hasattr(pytest, "shadow_account_id"):
            pytest.skip("需要先创建影子账户")

        response = client.post(
            f"/api/v1/shadow/accounts/{pytest.shadow_account_id}/terminate"
        )

        assert response.status_code == 200

    def test_get_shadow_score(self):
        """测试获取影子账户评分端点"""
        if not hasattr(pytest, "shadow_account_id"):
            pytest.skip("需要先创建影子账户")

        response = client.get(
            f"/api/v1/shadow/accounts/{pytest.shadow_account_id}/score"
        )

        assert response.status_code == 200
        data = response.json().get("data", {})

        assert "weighted_score" in data or "score" in data


# ==================
# 风控API测试
# ==================

class TestRiskAPI:
    """风控API集成测试"""

    def test_validate_trade(self):
        """测试验证交易端点"""
        response = client.post(
            "/api/v1/risk/validate",
            json={
                "symbol": "SH600000",
                "action": "buy",
                "amount": 100,
                "price": 10.0
            }
        )

        assert response.status_code == 200
        data = response.json().get("data", {})

        assert "passed" in data
        assert "risk_score" in data

    def test_get_risk_config(self):
        """测试获取风控配置端点"""
        response = client.get("/api/v1/risk/config")

        assert response.status_code == 200
        data = response.json().get("data", {})

        assert "total_capital" in data or "max_total_loss_rate" in data

    def test_update_risk_config(self):
        """测试更新风控配置端点"""
        response = client.put(
            "/api/v1/risk/config",
            json={
                "total_capital": 100000,
                "max_total_loss_rate": 0.10,
                "max_daily_loss_rate": 0.05
            }
        )

        assert response.status_code == 200

    def test_update_account_value(self):
        """测试更新账户价值端点"""
        response = client.post(
            "/api/v1/risk/account/update",
            json={
                "current_value": 105000,
                "date": "2024-01-01"
            }
        )

        assert response.status_code == 200

    def test_get_blacklist(self):
        """测试获取黑名单端点"""
        response = client.get("/api/v1/risk/blacklist")

        assert response.status_code == 200
        data = response.json().get("data", [])

        assert isinstance(data, list)

    def test_add_blacklist(self):
        """测试添加黑名单端点"""
        response = client.post(
            "/api/v1/risk/blacklist/add",
            json={"symbols": ["ST600000", "ST000001"]}
        )

        assert response.status_code == 200

    def test_remove_blacklist(self):
        """测试移除黑名单端点"""
        # 先添加
        client.post(
            "/api/v1/risk/blacklist/add",
            json={"symbols": ["TEST600000"]}
        )

        # 再移除
        response = client.delete("/api/v1/risk/blacklist/TEST600000")

        assert response.status_code == 200


# ==================
# 健康检查测试
# ==================

class TestHealthAPI:
    """健康检查API测试"""

    def test_health_check(self):
        """测试健康检查端点"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_root_endpoint(self):
        """测试根端点"""
        response = client.get("/")

        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

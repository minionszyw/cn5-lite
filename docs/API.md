# CN5-Lite API文档

## 📋 概述

CN5-Lite提供27个RESTful API端点，覆盖策略管理、回测、交易、影子账户和风控等功能。

**基础URL**: `http://localhost:8000/api/v1`

**认证**: 暂无（后续可添加JWT）

**响应格式**: JSON

---

## 📚 目录

- [策略管理API](#策略管理api)
- [回测API](#回测api)
- [交易管理API](#交易管理api)
- [影子账户API](#影子账户api)
- [风控API](#风控api)
- [错误码](#错误码)

---

## 策略管理API

### 1. 生成策略

**端点**: `POST /api/v1/strategies/generate`

**描述**: 使用AI生成策略代码

**请求体**:
```json
{
  "user_input": "双均线策略，MA5上穿MA20买入",
  "context": {
    "symbol": "SH600000",
    "stop_loss": 0.10
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "name": "MAStrategy",
    "code": "class MAStrategy:\n    def on_bar(self, bar):\n        ...",
    "params": {
      "ma_short": 5,
      "ma_long": 20
    },
    "security_check": {
      "safe": true,
      "message": "代码安全"
    }
  }
}
```

### 2. 创建策略

**端点**: `POST /api/v1/strategies`

**请求体**:
```json
{
  "name": "MyStrategy",
  "code": "class MyStrategy:...",
  "params": {"period": 20},
  "status": "draft"
}
```

**响应**:
```json
{
  "id": 1,
  "name": "MyStrategy",
  "status": "draft",
  "created_at": "2024-01-01T00:00:00"
}
```

### 3. 获取策略

**端点**: `GET /api/v1/strategies/{id}`

**响应**:
```json
{
  "id": 1,
  "name": "MyStrategy",
  "code": "class MyStrategy:...",
  "params": {"period": 20},
  "status": "draft",
  "annual_return": 0.25,
  "sharpe_ratio": 1.8,
  "created_at": "2024-01-01T00:00:00"
}
```

### 4. 策略列表

**端点**: `GET /api/v1/strategies`

**查询参数**:
- `status` (可选): draft/shadow/live
- `limit` (可选): 默认10
- `offset` (可选): 默认0

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Strategy1",
      "status": "live",
      "annual_return": 0.30
    }
  ],
  "total": 50,
  "limit": 10,
  "offset": 0
}
```

### 5. 删除策略

**端点**: `DELETE /api/v1/strategies/{id}`

**响应**:
```json
{
  "success": true,
  "message": "策略已删除"
}
```

### 6. 验证策略

**端点**: `POST /api/v1/strategies/{id}/validate`

**响应**:
```json
{
  "success": true,
  "data": {
    "valid": true,
    "safe": true,
    "complexity": 15,
    "message": "验证通过"
  }
}
```

---

## 回测API

### 1. 运行回测

**端点**: `POST /api/v1/backtest/run`

**请求体**:
```json
{
  "strategy_id": 1,
  "symbol": "SH600000",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_cash": 100000,
  "enable_china_rules": true
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "annual_return": 0.28,
    "sharpe_ratio": 1.85,
    "max_drawdown": 0.12,
    "win_rate": 0.58,
    "total_trades": 127,
    "final_value": 128000,
    "equity_curve": [
      {"date": "2024-01-01", "value": 100000},
      {"date": "2024-01-02", "value": 100500}
    ],
    "trades": [
      {
        "date": "2024-01-02",
        "action": "buy",
        "symbol": "SH600000",
        "price": 10.0,
        "amount": 100,
        "commission": 30.0
      }
    ],
    "china_rules_applied": true
  }
}
```

### 2. 快速回测

**端点**: `POST /api/v1/backtest/quick`

**请求体**:
```json
{
  "strategy_id": 1,
  "symbol": "SH600000",
  "days": 30
}
```

**响应**: 同上

---

## 交易管理API

### 1. 启动自动交易

**端点**: `POST /api/v1/trading/start`

**请求体**:
```json
{
  "strategy_id": 1,
  "require_approval": false
}
```

**响应**:
```json
{
  "success": true,
  "message": "自动交易已启动"
}
```

### 2. 停止自动交易

**端点**: `POST /api/v1/trading/stop`

**请求体**:
```json
{
  "close_positions": true
}
```

**响应**:
```json
{
  "success": true,
  "message": "自动交易已停止，所有持仓已平仓"
}
```

### 3. 获取交易状态

**端点**: `GET /api/v1/trading/status`

**响应**:
```json
{
  "success": true,
  "data": {
    "is_running": true,
    "active_strategies": 3,
    "today_trades": 15,
    "today_pnl": 1250.50,
    "running_strategies": [
      {
        "id": 1,
        "name": "Strategy1",
        "positions_count": 2,
        "today_pnl": 500.0
      }
    ]
  }
}
```

### 4. 获取交易记录

**端点**: `GET /api/v1/trading/trades/{strategy_id}`

**查询参数**:
- `start_date` (可选)
- `end_date` (可选)
- `limit` (可选)

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "trade_time": "2024-01-01T10:30:00",
      "symbol": "SH600000",
      "action": "buy",
      "price": 10.5,
      "volume": 100,
      "amount": 1050.0,
      "commission": 31.5,
      "tax": 0,
      "pnl": -31.5
    }
  ]
}
```

### 5. 手动执行交易

**端点**: `POST /api/v1/trading/execute`

**请求体**:
```json
{
  "symbol": "SH600000",
  "action": "buy",
  "amount": 100,
  "price": 10.0
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "order_id": "ORD123456",
    "status": "filled"
  }
}
```

### 6. 恢复策略状态

**端点**: `POST /api/v1/trading/rehydrate/{strategy_id}`

**响应**:
```json
{
  "success": true,
  "data": {
    "positions": {
      "SH600000": {
        "amount": 100,
        "cost_price": 10.0
      }
    },
    "indicators_restored": true,
    "locked_positions": {
      "SH600001": 100
    }
  }
}
```

---

## 影子账户API

### 1. 创建影子账户

**端点**: `POST /api/v1/shadow/accounts`

**请求体**:
```json
{
  "strategy_id": 1,
  "initial_cash": 100000,
  "observation_days": 7
}
```

**响应**:
```json
{
  "id": 1,
  "strategy_id": 1,
  "status": "running",
  "created_at": "2024-01-01T00:00:00"
}
```

### 2. 获取影子账户

**端点**: `GET /api/v1/shadow/accounts/{id}`

**响应**:
```json
{
  "id": 1,
  "strategy_id": 1,
  "strategy_name": "MyStrategy",
  "status": "running",
  "observation_days": 7,
  "weighted_score": 42.5,
  "ranking": 3,
  "annual_return": 0.35,
  "sharpe_ratio": 2.1,
  "max_drawdown": 0.08,
  "volatility": 0.12,
  "win_rate": 0.65
}
```

### 3. Top策略排行

**端点**: `GET /api/v1/shadow/top`

**查询参数**:
- `limit` (可选): 默认10
- `min_score` (可选): 默认30.0

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "strategy_name": "BestStrategy",
      "weighted_score": 48.5,
      "ranking": 1,
      "annual_return": 0.42,
      "can_promote": true
    }
  ]
}
```

### 4. 晋升到实盘

**端点**: `POST /api/v1/shadow/accounts/{id}/promote`

**响应**:
```json
{
  "success": true,
  "message": "已晋升到实盘"
}
```

### 5. 终止影子账户

**端点**: `POST /api/v1/shadow/accounts/{id}/terminate`

**响应**:
```json
{
  "success": true,
  "message": "影子账户已终止"
}
```

### 6. 获取账户评分

**端点**: `GET /api/v1/shadow/accounts/{id}/score`

**响应**:
```json
{
  "success": true,
  "data": {
    "weighted_score": 42.5,
    "scores": {
      "annual_return": 35.0,
      "sharpe_ratio": 52.5,
      "max_drawdown": 40.0,
      "volatility": 50.0,
      "win_rate": 65.0
    },
    "weights": {
      "annual_return": 0.30,
      "sharpe_ratio": 0.25,
      "max_drawdown": 0.20,
      "volatility": 0.15,
      "win_rate": 0.10
    }
  }
}
```

---

## 风控API

### 1. 验证交易

**端点**: `POST /api/v1/risk/validate`

**请求体**:
```json
{
  "symbol": "SH600000",
  "action": "buy",
  "amount": 100,
  "price": 10.0
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "passed": true,
    "risk_score": 25,
    "reason": null
  }
}
```

### 2. 获取风控配置

**端点**: `GET /api/v1/risk/config`

**响应**:
```json
{
  "success": true,
  "data": {
    "total_capital": 100000,
    "max_total_loss_rate": 0.10,
    "max_daily_loss_rate": 0.05,
    "max_strategy_capital_rate": 0.30,
    "max_single_trade_rate": 0.20,
    "max_trades_per_hour": 20,
    "enable_limit_check": true
  }
}
```

### 3. 更新风控配置

**端点**: `PUT /api/v1/risk/config`

**请求体**:
```json
{
  "total_capital": 200000,
  "max_total_loss_rate": 0.08
}
```

**响应**:
```json
{
  "success": true,
  "message": "配置已更新"
}
```

### 4. 更新账户价值

**端点**: `POST /api/v1/risk/account/update`

**请求体**:
```json
{
  "current_value": 105000,
  "date": "2024-01-01"
}
```

**响应**:
```json
{
  "success": true,
  "message": "账户价值已更新"
}
```

### 5. 获取黑名单

**端点**: `GET /api/v1/risk/blacklist`

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "symbol": "ST600000",
      "added_at": "2024-01-01T00:00:00"
    }
  ]
}
```

### 6. 添加黑名单

**端点**: `POST /api/v1/risk/blacklist/add`

**请求体**:
```json
{
  "symbols": ["ST600000", "ST600001"]
}
```

**响应**:
```json
{
  "success": true,
  "message": "已添加2个股票到黑名单"
}
```

### 7. 移除黑名单

**端点**: `DELETE /api/v1/risk/blacklist/{symbol}`

**响应**:
```json
{
  "success": true,
  "message": "已从黑名单移除"
}
```

---

## 错误码

### HTTP状态码

- `200` - 成功
- `201` - 创建成功
- `400` - 请求参数错误
- `404` - 资源不存在
- `500` - 服务器错误

### 业务错误码

```json
{
  "success": false,
  "error": {
    "code": "STRATEGY_NOT_FOUND",
    "message": "策略不存在",
    "details": {}
  }
}
```

**错误码列表**:

| 错误码 | 说明 |
|--------|------|
| `STRATEGY_NOT_FOUND` | 策略不存在 |
| `INVALID_PARAMS` | 参数无效 |
| `CODE_NOT_SAFE` | 策略代码不安全 |
| `BACKTEST_FAILED` | 回测执行失败 |
| `RISK_BLOCKED` | 风控拦截 |
| `TRADING_NOT_RUNNING` | 交易未启动 |
| `SHADOW_NOT_READY` | 影子账户未就绪 |
| `INSUFFICIENT_CAPITAL` | 资金不足 |
| `DATA_SOURCE_ERROR` | 数据源错误 |
| `AI_TIMEOUT` | AI调用超时 |

---

## 使用示例

### Python

```python
import requests

# 生成策略
response = requests.post(
    "http://localhost:8000/api/v1/strategies/generate",
    json={
        "user_input": "双均线策略",
        "context": {}
    }
)

data = response.json()
print(data['data']['code'])
```

### JavaScript

```javascript
// 获取策略列表
fetch('http://localhost:8000/api/v1/strategies?limit=10')
  .then(res => res.json())
  .then(data => console.log(data.data));
```

### cURL

```bash
# 启动交易
curl -X POST http://localhost:8000/api/v1/trading/start \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": 1, "require_approval": false}'
```

---

## 速率限制

暂无限制（后续可添加）

---

## WebSocket（规划中）

实时推送交易信号和账户状态：

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Trade signal:', data);
};
```

---

**最后更新**: 2025-11-30
**API版本**: v1

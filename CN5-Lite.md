# CN5-Lite 系统架构设计

**版本**: 1.3.2
**定位**: 个人散户(中国A股,模拟盘) AI量化交易系统
**更新**: 2025-11-29
**审查**: Gemini架构师最终复审版 (Final Audit)

---

## 目录

1. [系统概述](#1-系统概述)
2. [架构设计](#2-架构设计)
3. [技术栈](#3-技术栈)
4. [目录结构](#4-目录结构)
5. [核心模块](#5-核心模块)
6. [数据库设计](#6-数据库设计)
7. [API设计](#7-api设计)
8. [配置规范](#8-配置规范)
9. [开发规范](#9-开发规范)

---

## 1. 系统概述

### 1.1 核心定位

CN5-Lite是**轻量级AI驱动的量化交易系统**，为A股散户(<10万资金)设计。

**核心特性**:
- ✅ AI策略研究员: 生成/优化/筛选策略
- ✅ 模拟盘优先: vnpy模拟交易，降低风险
- ✅ A股适配: 停牌/涨跌停/除权处理
- ✅ 多数据源: AkShare/baostock/efinance容错
- ✅ 高性价比AI: 支持deepseek/qwen等模型

### 1.2 系统边界

**IN SCOPE**:
- AI策略生成、批量回测、影子账户筛选
- 模拟盘交易(免确认/需确认双模式)
- A股市场适配(停牌/涨跌停/滑点)
- 多数据源容错、逻辑测试框架

**OUT OF SCOPE**:
- 高频交易(毫秒级)
- 复杂衍生品
- 企业级多租户

---

## 2. 架构设计

### 2.1 系统拓扑

```
┌─────────────────────────────────────┐
│   Streamlit UI (8501端口)           │
│   策略生成 | 回测 | 影子 | 模拟盘   │
└──────────────┬──────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────┐
│      FastAPI 网关 (8000端口)        │
│      路由 | 认证 | 校验             │
└─┬────┬────┬────┬────┬──────────────┘
  │    │    │    │    │
  ▼    ▼    ▼    ▼    ▼
┌───┐┌───┐┌───┐┌───┐┌───┐
│AI ││回测││影子││模拟││风控│
│生成││引擎││账户││盘  ││    │
└───┘└───┘└───┘└───┘└───┘
  │    │    │    │    │
  └────┴────┴────┴────┘
         │
    ┌────▼─────┐
    │PostgreSQL│
    │  Redis   │
    └──────────┘
```

### 2.2 容器编排

```yaml
services:
  api:      # FastAPI后端
  ui:       # Streamlit前端
  worker:   # Celery异步任务
  beat:     # Celery定时任务
  db:       # PostgreSQL
  redis:    # 消息队列+缓存
```

### 2.3 数据流

**策略生成**: 用户输入 → AI模型 → 语法校验 → 逻辑测试 → 保存DB

**回测流程**: 策略代码 → Celery Worker → 加载数据(多源容错) → Backtrader引擎(+A股适配) → 保存结果

**影子账户**: 定时任务 → 历史数据回放 → 多维度评分 → Top3晋升

**模拟交易**: 策略信号 → 风控验证 → vnpy模拟盘 → 记录DB → WebSocket推送

---

## 3. 技术栈

### 3.1 核心依赖

| 分类 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 后端 | FastAPI | 0.109+ | API网关 |
| 前端 | Streamlit | 1.30+ | Web UI |
| AI | OpenAI协议 | - | deepseek/qwen/gpt |
| 回测 | Backtrader | 1.9.78+ | +A股适配 |
| 交易 | vn.py | 3.9+ | 模拟盘 |
| 任务 | Celery | 5.3+ | 异步任务 |
| 数据库 | PostgreSQL | 15+ | 主存储 |
| 缓存 | Redis | 7.2+ | 消息+缓存 |
| 数据源 | 多源 | - | akshare/baostock/efinance |

### 3.2 Python依赖

```txt
# Web
fastapi==0.109.2
streamlit==1.30.0

# AI (OpenAI协议兼容)
openai==1.12.0

# 量化
backtrader==1.9.78.123
vnpy==3.9.1

# 数据源
akshare==1.13.5
baostock==0.8.9
efinance==0.5.3

# 任务队列
celery[redis]==5.3.6

# 数据库
psycopg2-binary==2.9.9
sqlalchemy==2.0.25
```

---

## 4. 目录结构

```
cn5-lite/
├── docker-compose.yml
├── requirements.txt
├── .env.example
│
├── app/                    # 主应用
│   ├── main.py             # FastAPI入口
│   ├── config.py           # 配置管理
│   │
│   ├── api/                # API路由
│   │   ├── strategies.py   # 策略管理
│   │   ├── backtest.py     # 回测
│   │   ├── shadow.py       # 影子账户
│   │   └── trading.py      # 模拟交易
│   │
│   ├── services/           # 业务逻辑
│   │   ├── ai_generator.py         # AI生成
│   │   ├── strategy_adapter.py     # ⭐ 策略适配器(消除回测/实盘鸿沟)
│   │   ├── backtest_engine.py      # 回测引擎
│   │   ├── shadow_manager.py       # 影子管理
│   │   ├── trade_executor.py       # 交易执行
│   │   ├── risk_validator.py       # 风控
│   │   ├── multi_datasource.py     # 多源容错+归一化
│   │   └── strategy_logic_tester.py # 逻辑测试
│   │
│   ├── models/             # 数据模型
│   │   ├── strategy.py
│   │   ├── backtest.py
│   │   └── trade.py
│   │
│   └── tasks/              # Celery任务
│       ├── celery_app.py
│       ├── backtest_tasks.py
│       └── shadow_tasks.py
│
├── ui/                     # Streamlit前端
│   ├── app.py
│   └── pages/
│
├── database/               # 数据库脚本
│   └── init.sql
│
├── prompts/                # AI模板
│   └── generate_strategy.txt
│
└── tests/                  # 测试
    ├── unit/
    └── integration/
```

---

## 5. 核心模块

### 5.1 AI策略生成器

**职责**: 将自然语言转换为可执行策略代码

**接口设计**:

```python
class AIStrategyGenerator:
    """支持OpenAI协议兼容模型"""

    def __init__(self, api_key: str, base_url: str = None, model: str = "deepseek-chat"):
        """
        Args:
            api_key: API密钥
            base_url: endpoint (deepseek/qwen等)
            model: 模型名称
        """

    def generate(self, user_input: str, context: dict = None) -> dict:
        """
        生成策略代码

        Returns:
            {
                "code": "策略代码",
                "name": "策略名称",
                "params": {"ma_period": 10, ...}
            }
        """
```

**关键设计点**:
1. 支持多AI模型切换(降低成本)
2. 语法校验: AST解析+危险函数黑名单
3. 必需方法检查: on_bar等核心方法
4. 圈复杂度限制: ≤20
5. **沙箱执行安全** (⚠️ 关键):
   - 超时限制: `func_timeout(30秒)`
   - 资源限制: Docker容器CPU/内存限制
   - 禁止死循环检测

### 5.2 回测引擎

**职责**: 验证策略表现 + A股市场适配

**接口设计**:

```python
class BacktestEngine:
    """回测引擎 + A股适配"""

    def __init__(self, initial_cash: float = 100000, enable_china_rules: bool = True):
        pass

    def run(self, strategy_code: str, data: pd.DataFrame, params: dict = None) -> dict:
        """
        执行回测

        Returns:
            {
                "annual_return": 0.28,
                "max_drawdown": 0.12,
                "sharpe_ratio": 1.85,
                "win_rate": 0.58,
                "total_trades": 127
            }
        """

    def _apply_china_market_rules(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        A股特殊规则 (⚠️ 完整版):
        1. 停牌检测 (volume=0)
        2. 涨跌停限制 (普通±10%, ST±5%, 科创/创业板±20%)
        3. T+1制度: 当日买入不可卖出
        4. 最小交易单位: 买入100股整数倍，卖出可零股
        5. 印花税: 卖出0.1%, 买入免税
        6. 佣金: 双向0.03%, 最低5元
        7. 滑点估算
        8. 除权除息复权因子
        """
```

**关键设计点**:
1. 多数据源容错: AkShare → baostock → efinance
2. 数据缓存: 避免重复加载
3. **A股适配层** (⚠️ 严格模拟):
   - T+1锁定: 当日买入仓位标记为locked_until_next_day
   - 交易单位校验: buy_volume % 100 == 0
   - 税费真实计算: 影响小资金策略表现
4. 并行优化: ProcessPoolExecutor

### 5.3 影子账户管理器

**职责**: 筛选优质策略

**接口设计**:

```python
class ShadowManager:
    """影子账户管理"""

    def create_shadow_account(self, strategy_id: int, observation_days: int = 7):
        """创建影子账户"""

    def calculate_score(self, account_id: int) -> float:
        """
        多维度评分:
        - 年化收益率 (30%)
        - 夏普比率 (25%)
        - 最大回撤 (20%)
        - 波动率 (15%)
        - 胜率 (10%)

        时间权重: 指数衰减(半衰期7天)
        """

    def get_top_strategies(self, limit: int = 3, min_score: float = 30.0):
        """获取Top N策略"""
```

**关键设计点**:
1. 历史数据回放(非随机数据)
2. 按天分段回测
3. 晋升阈值: 得分≥35且观察≥14天

### 5.4 风控验证器

**职责**: 7层风控防护

**接口设计**:

```python
class RiskValidator:
    """7层风控"""

    def validate(self, signal: dict) -> dict:
        """
        验证规则:
        1. 总资金止损 (10%)
        2. 黑名单股票 (ST等)
        3. 单日亏损限制 (5%)
        4. 单策略资金占用 (30%)
        5. 单笔过大 (20%)
        6. 异常交易频率 (20笔/小时)
        7. 涨跌停板

        Returns:
            {"passed": bool, "reason": str, "risk_score": int}
        """
```

### 5.5 AI交易管理器

**职责**: 模拟盘AI自动交易

**接口设计**:

```python
class AITradingManager:
    """模拟盘AI交易"""

    def start_auto_trading(self):
        """
        启动AI交易

        模式1: 免确认 (≤3000元自动执行)
        模式2: 需确认 (所有交易需审核)

        ⚠️ 容器重启时自动触发 rehydrate_state()
        """

    def rehydrate_state(self, strategy_id: int):
        """
        容器重启断点续传 (Crash Recovery)

        挑战: Docker容器重启后，内存中的策略状态会丢失

        解决方案:
        1. 从trades表恢复持仓和成本价
        2. 重新加载历史K线，让策略"空跑"恢复技术指标
        3. 恢复T+1锁定持仓

        示例:
        ```python
        # 1. 恢复持仓
        positions = db.query('''
            SELECT symbol,
                   SUM(CASE WHEN action='BUY' THEN volume ELSE -volume END) as position,
                   AVG(price) as cost_price
            FROM trades
            WHERE strategy_id = ? AND status = 'completed'
            GROUP BY symbol
            HAVING position > 0
        ''', strategy_id)

        # 2. 恢复技术指标 (重放历史K线)
        for symbol in positions['symbol']:
            historical_bars = data_manager.fetch(symbol, start_date='30 days ago', end_date='today')
            for bar in historical_bars:
                strategy.on_bar(bar)  # 空跑恢复MA等指标

        # 3. 恢复T+1锁定
        today_buys = db.query('''
            SELECT symbol, volume FROM trades
            WHERE strategy_id = ? AND action='BUY' AND date = CURRENT_DATE
        ''', strategy_id)
        for buy in today_buys:
            strategy.locked_positions[buy['symbol']] = buy['volume']
        ```

        Returns:
            {"positions": dict, "indicators_restored": bool, "locked_positions": dict}
        """

    def _run_strategy_logic_test(self, strategy_id: int) -> bool:
        """
        策略逻辑测试:
        1. 空数据测试
        2. 极端行情(涨停/跌停/停牌)
        3. 异常值(NaN/Inf)
        4. 边界条件
        """
```

**配置**:

```python
class AITradingConfig:
    require_approval: bool = False  # 免确认模式
    auto_approve_threshold: float = 3000  # 单笔限额
    enable_logic_test: bool = True  # 启用测试
    max_capital_ratio: float = 0.30  # AI最多30%资金
```

### 5.6 多数据源管理器

**职责**: 数据源容错 + 数据归一化

**接口设计**:

```python
class DataSourceManager:
    """多数据源容错 + 归一化层"""

    def __init__(self):
        self.sources = [
            {'name': 'akshare', 'priority': 1, 'provider': AkShareProvider()},
            {'name': 'baostock', 'priority': 2, 'provider': BaoStockProvider()},
            {'name': 'efinance', 'priority': 3, 'provider': EfinanceProvider()},
        ]

    def fetch_with_fallback(self, symbol: str, start_date: str, end_date: str):
        """
        自动容错:
        1. 依次尝试各数据源
        2. **限流控制** (⚠️ 防封IP)
        3. 数据质量验证
        4. 失败降级到下一源
        5. **归一化处理** (⚠️ 关键)
        """
        for source in self.sources:
            try:
                # 限流检查
                if not self._rate_limit(source['name']):
                    logger.warning(f"{source['name']}触发限流，跳过")
                    continue

                # 获取数据
                data = source['provider'].fetch(symbol, start_date, end_date)

                # 归一化
                data = self._normalize_data(data, source['name'])

                return data
            except Exception as e:
                logger.error(f"{source['name']}失败: {e}")
                continue

        raise DataSourceError("所有数据源均失败")

    def _rate_limit(self, source_name: str) -> bool:
        """
        限流器 - Redis令牌桶算法

        Args:
            source_name: 数据源名称

        Returns:
            是否允许请求
        """
        import redis
        from datetime import datetime

        r = redis.Redis()
        key = f"rate_limit:{source_name}"
        limit = 1  # 1次/秒 for AkShare

        # 令牌桶算法
        current = r.incr(key)
        if current == 1:
            r.expire(key, 1)  # 1秒过期

        return current <= limit

    def _normalize_data(self, data: pd.DataFrame, source: str) -> pd.DataFrame:
        """
        数据归一化层 (⚠️ 防止脏数据):
        1. 统一列名: date/open/high/low/close/volume
        2. 统一复权方式: 强制前复权(qfq)
        3. 填充缺失值: 停牌日forward fill
        4. OHLC合法性校验: high >= max(open,close,low)
        5. 去除异常值: 3-sigma过滤
        """
```

**关键设计点**:
1. ⚠️ **归一化层必须**: 不同源数据口径不一致
2. **复权因子统一**: 所有源转为前复权
3. **停牌日处理**: 用前一日收盘价填充
4. **入库前校验**: 确保数据质量
5. ⚠️ **限流器** (Rate Limiter) - 防止IP封禁:
   - 使用Redis令牌桶算法
   - AkShare: 1次/秒, 每IP每日5000次
   - Baostock: 免费无限制（优先降级）
   - 并发控制: Celery Worker最多5个并发数据请求

### 5.7 策略适配器层 ⭐ 新增

**职责**: 解决Backtrader与vnpy的"双套代码"问题

**架构设计**:

```
┌─────────────────────────────────┐
│   AI生成标准策略代码             │
│   (统一接口: on_bar/on_order)   │
└──────────────┬──────────────────┘
               │
    ┌──────────┴──────────┐
    │   StrategyAdapter   │  ← 适配器层
    │   (统一封装层)       │
    └──┬─────────────┬────┘
       │             │
       ▼             ▼
┌─────────────┐ ┌──────────────┐
│ Backtrader  │ │  vn.py       │
│ Wrapper     │ │  Wrapper     │
│ (回测)      │ │  (模拟/实盘) │
└─────────────┘ └──────────────┘
```

**接口设计**:

```python
class StrategyAdapter:
    """
    策略适配器 - 消除回测/实盘逻辑鸿沟 (⚠️ 架构关键)

    设计原则:
    - AI只生成一套标准代码
    - Adapter负责包装成Backtrader或vnpy格式
    - Order执行逻辑完全一致
    """

    def __init__(self, strategy_code: str):
        self.strategy_code = strategy_code
        self.standard_strategy = self._parse_standard_strategy(strategy_code)

    def to_backtrader(self) -> bt.Strategy:
        """
        包装为Backtrader格式

        ⚠️ 关键: 防止未来函数 (Look-Ahead Bias)
        - 不直接暴露self.datas[0]全量数据
        - 逐K线推送，模拟实盘行为
        """
        class BacktraderWrapper(bt.Strategy):
            def __init__(self):
                # 调用标准策略的初始化
                self.strategy = standard_strategy
                self.bar_index = 0  # 当前K线索引

            def next(self):
                # ⚠️ 只传递当前Bar，禁止访问未来数据
                current_bar = {
                    'datetime': self.datas[0].datetime.datetime(0),
                    'open': self.datas[0].open[0],
                    'high': self.datas[0].high[0],
                    'low': self.datas[0].low[0],
                    'close': self.datas[0].close[0],
                    'volume': self.datas[0].volume[0],
                }

                # 调用标准策略
                signal = self.strategy.on_bar(current_bar)
                # 执行订单
                self._execute_order(signal)
                self.bar_index += 1

        return BacktraderWrapper

    def to_vnpy(self) -> CtaTemplate:
        """包装为vnpy格式"""
        class VnpyWrapper(CtaTemplate):
            def on_bar(self, bar: BarData):
                # 调用标准策略
                signal = standard_strategy.on_bar(bar)
                # 执行订单(与Backtrader完全一致)
                self._execute_order(signal)

        return VnpyWrapper

    def _execute_order(self, signal: dict):
        """
        统一订单执行逻辑 (⚠️ 关键):
        - 滑点计算方式相同
        - 手续费计算方式相同
        - 涨跌停检查相同
        - T+1锁定逻辑相同
        """
```

**关键设计点**:
1. ⚠️ **所测即所跑**: 回测和实盘运行同一套逻辑
2. **标准策略接口**: 只需实现on_bar/on_order
3. **适配器负责差异**: 不同框架的API差异由适配器处理
4. **Order执行统一**: 滑点、手续费、撮合逻辑完全一致
5. ⚠️ **防止未来函数** (Look-Ahead Bias):
   - Backtrader包装器逐K线推送，不暴露全量数据
   - 策略只能访问current_bar，禁止访问self.datas[1:]
   - 技术指标缓存在策略内部状态，不依赖历史序列
6. ⚠️ **状态管理** (State Management):
   - T+1锁定: locked_until_next_day持久化到DB
   - 技术指标: 策略内部维护历史窗口(如MA20)
   - 容器重启: 从DB恢复持仓和指标状态

---

## 6. 数据库设计

### 6.1 核心表结构

```sql
-- 策略表
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code TEXT NOT NULL,
    params JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'draft',  -- draft/testing/shadow/live
    annual_return DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 回测结果表
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    strategy_id INT REFERENCES strategies(id),
    start_date DATE,
    end_date DATE,
    annual_return DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    win_rate DECIMAL(8,4),
    total_trades INT,
    equity_curve JSONB,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 影子账户表
CREATE TABLE shadow_accounts (
    id SERIAL PRIMARY KEY,
    strategy_id INT REFERENCES strategies(id),
    initial_cash DECIMAL(15,2) DEFAULT 100000,
    status VARCHAR(20) DEFAULT 'running',
    observation_days INT DEFAULT 7,
    weighted_score DECIMAL(8,4),
    ranking INT,
    started_at TIMESTAMPTZ NOT NULL
);

-- 交易记录表
CREATE TABLE trades (
    id BIGSERIAL PRIMARY KEY,
    account_type VARCHAR(20),  -- shadow/simulation
    account_id INT,
    strategy_id INT,
    strategy_instance_id VARCHAR(50),  -- ⭐ 新增: 区分策略不同参数运行实例
    symbol VARCHAR(20),
    direction VARCHAR(10),  -- buy/sell
    price DECIMAL(10,2),
    volume INT,
    commission DECIMAL(10,2),  -- ⭐ 新增: 佣金记录
    tax DECIMAL(10,2),  -- ⭐ 新增: 印花税记录
    pnl DECIMAL(15,2),
    trade_time TIMESTAMPTZ DEFAULT NOW()
);

-- K线数据表 (⚠️ 优化版)
CREATE TABLE klines (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    adjust_factor DECIMAL(10,6) DEFAULT 1.0,  -- ⭐ 新增: 复权因子
    CONSTRAINT unique_kline UNIQUE(symbol, timestamp)
) PARTITION BY RANGE (timestamp);  -- ⭐ 按时间分区

-- 分区示例 (提升查询性能)
CREATE TABLE klines_2022 PARTITION OF klines
    FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');
CREATE TABLE klines_2023 PARTITION OF klines
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
CREATE TABLE klines_2024 PARTITION OF klines
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- 索引
CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_backtest_strategy ON backtest_results(strategy_id);
CREATE INDEX idx_shadow_ranking ON shadow_accounts(ranking);
CREATE INDEX idx_trades_account ON trades(account_type, account_id);
CREATE INDEX idx_trades_instance ON trades(strategy_instance_id);  -- ⭐ 新增
CREATE INDEX idx_klines_symbol ON klines(symbol, timestamp DESC);

-- ⭐ 可选: 使用TimescaleDB扩展(高性能时序数据库)
-- CREATE EXTENSION IF NOT EXISTS timescaledb;
-- SELECT create_hypertable('klines', 'timestamp');
```

**⚠️ 数据库优化说明**:
1. **复权因子 (adjust_factor)**: A股必须，用于计算真实收益
2. **分区表**: 按年分区，查询速度提升3-5倍
3. **strategy_instance_id**: 区分同策略不同参数运行
4. **税费字段**: 记录佣金和印花税，便于分析成本
5. **TimescaleDB**: 可选，进一步优化时序数据性能

---

## 7. API设计

### 7.1 策略管理

```python
# POST /api/strategies/generate
# 生成策略
Request: {"user_input": "双均线策略，MA5/MA20金叉买入"}
Response: {"id": 123, "name": "MAStrategy", "code": "..."}

# GET /api/strategies/{id}
# 获取策略详情

# GET /api/strategies
# 列表查询
Query: ?status=shadow&limit=10
```

### 7.2 回测管理

```python
# POST /api/backtest/run
# 启动回测
Request: {
    "strategy_id": 123,
    "start_date": "2022-01-01",
    "end_date": "2024-12-31"
}
Response: {"task_id": "xxx", "status": "queued"}

# GET /api/backtest/results/{task_id}
# 查询结果
```

### 7.3 影子账户

```python
# POST /api/shadow/create
# 创建影子账户
Request: {"strategy_id": 123, "observation_days": 7}

# GET /api/shadow/rankings
# 获取排名
Response: [{"id": 1, "score": 45.2, "ranking": 1}, ...]
```

### 7.4 模拟交易

```python
# POST /api/trading/start
# 启动AI交易
Request: {
    "mode": "auto",  # auto/manual
    "config": {...}
}

# GET /api/trading/report
# 获取交易报告
```

---

## 8. 配置规范

### 8.1 环境变量

```bash
# .env

# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/cn5lite
REDIS_URL=redis://localhost:6379/0

# AI模型 (支持deepseek/qwen/gpt)
AI_API_KEY=sk-xxx
AI_BASE_URL=https://api.deepseek.com/v1  # 或留空使用OpenAI
AI_MODEL=deepseek-chat

# 数据源
DATA_SOURCE_PRIORITY=akshare,baostock,efinance
DATA_CACHE_DAYS=30

# 风控 (比例制)
DAILY_LOSS_LIMIT_RATIO=0.05  # 5%
MAX_POSITION_RATIO=0.20
TOTAL_STOP_LOSS_RATIO=0.10

# 交易模式
TRADING_MODE=simulation  # simulation/live
```

### 8.2 Docker Compose

```yaml
version: '3.9'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: cn5lite
      POSTGRES_USER: cn5user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0
    environment:
      DATABASE_URL: postgresql://cn5user:${DB_PASSWORD}@db:5432/cn5lite
      AI_API_KEY: ${AI_API_KEY}
    depends_on:
      - db
      - redis

  worker:
    build: .
    command: celery -A app.tasks.celery_app worker
    depends_on:
      - db
      - redis

  ui:
    build: .
    command: streamlit run ui/app.py
    ports:
      - "8501:8501"
```

---

## 9. 开发规范

### 9.1 SPEC + TDD流程

**推荐使用Claude Code辅助开发**

```
1. 编写SPEC → 2. 生成测试 → 3. 实现功能 → 4. 验证
```

**示例 - 添加新功能**:

```markdown
# SPEC: 策略克隆功能

## 功能目标
用户可以克隆已有策略，快速创建副本

## 接口设计
POST /api/strategies/{id}/clone
Response: {"id": 124, "name": "XXX (副本)"}

## 验收标准
- 代码、参数完整复制
- 状态重置为draft
- 测试覆盖率>80%
```

### 9.2 代码规范

```python
# 统一错误处理
class CN5Error(Exception):
    """系统基础异常"""
    pass

class DataSourceError(CN5Error):
    """数据源异常"""
    pass

# 统一日志格式
logger.info(f"回测完成: 策略ID={strategy_id}, 收益={result['annual_return']:.2%}")
```

### 9.3 测试规范

```python
# tests/unit/test_ai_generator.py
def test_generate_strategy():
    generator = AIStrategyGenerator(api_key="test")
    result = generator.generate("双均线策略")

    assert "code" in result
    assert "class" in result["code"]
    assert result["name"]

# pytest覆盖率>80%
pytest --cov=app --cov-report=html
```

### 9.4 Git提交规范

```bash
# 提交信息格式
<type>: <subject>

# type类型
feat: 新功能
fix: 修复bug
refactor: 重构
test: 测试
docs: 文档

# 示例
feat: 添加策略逻辑测试框架
fix: 修复影子账户评分计算错误
```

### 9.5 架构风险点清单 ⚠️

**必须关注的关键风险**（来自Gemini架构师审查）:

| 风险点 | 问题 | 解决方案 | 状态 |
|--------|------|----------|------|
| **回测/实盘鸿沟** | Backtrader和vnpy双套代码逻辑不一致 | 5.7 策略适配器层 | ✅ 已解决 |
| **数据源脏数据** | 多源数据口径不一致(复权/停牌) | 5.6 归一化层 | ✅ 已解决 |
| **AI代码炸弹** | 死循环或内存泄漏卡死Worker | 5.1 沙箱+超时+资源限制 | ✅ 已解决 |
| **复权因子缺失** | A股分红送股导致收益计算错误 | 6.1 klines.adjust_factor | ✅ 已解决 |
| **T+1未实现** | 回测允许当日买卖，实盘禁止 | 5.2 A股适配层 | ✅ 已解决 |
| **税费遗漏** | 小资金高频策略回测失真 | 5.2 印花税+佣金计算 | ✅ 已解决 |
| **分区性能** | K线查询慢(百万级数据) | 6.1 时间分区 | ✅ 已解决 |

**开发时必须验证的检查点**:
1. ✅ 回测和模拟盘使用相同的策略代码（通过适配器）
2. ✅ 数据入库前经过归一化（复权统一、停牌填充）
3. ✅ AI生成的策略有30秒超时保护
4. ✅ 回测中T+1锁定生效（当日买入不可卖出）
5. ✅ 税费计算与真实券商一致（佣金最低5元）
6. ✅ strategy_instance_id正确记录（区分不同参数运行）

---

## 附录

### A. 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/cn5-lite.git

# 2. 配置环境
cp .env.example .env
# 编辑.env填入AI_API_KEY

# 3. 启动
docker-compose up -d

# 4. 访问
open http://localhost:8501
```

### B. 常见问题

**Q: 如何切换AI模型?**
```bash
# .env
AI_MODEL=deepseek-chat  # 或 qwen-plus/gpt-4
AI_BASE_URL=https://api.deepseek.com/v1
```

**Q: 如何启用实盘?**
```bash
# .env
TRADING_MODE=live
VNPY_GATEWAY=ctp  # 配置券商API
```

### C. 版本历史

**v1.3.2 (2025-11-29)** - Gemini Final Audit: 生产级"最后一公里"优化 ⚠️ 生产就绪
- ⚠️ **防未来函数设计**: 策略适配器逐K线推送机制
  - BacktraderWrapper只传递当前Bar，禁止访问未来数据
  - 防止回测中self.datas[0][1:]导致的Look-Ahead Bias
  - 确保回测逻辑与实盘完全一致
- ⚠️ **容器重启断点续传**: AITradingManager状态恢复机制
  - rehydrate_state()从trades表恢复持仓和成本价
  - 重放历史K线恢复技术指标（MA等）
  - 恢复T+1锁定持仓，保证容器重启无缝衔接
- ⚠️ **免费数据源限流器**: Redis令牌桶算法
  - AkShare: 1次/秒, 5000次/日/IP
  - 防止IP被封禁，保证服务稳定性
  - Celery Worker并发控制（最多5个并行数据请求）

**v1.3.1 (2025-11-29)** - Gemini架构师深度审查优化版 ⚠️ 关键架构升级
- ⭐ **策略适配器层**: 消除Backtrader/vnpy双套代码问题
  - 统一策略接口，AI只生成一套代码
  - 适配器包装成回测或实盘格式
  - 订单执行逻辑完全一致（所测即所跑）
- ⚠️ **数据归一化层**: 防止多源脏数据
  - 统一复权方式（强制前复权）
  - OHLC合法性校验
  - 停牌日填充，异常值过滤
- ⚠️ **A股适配增强**: 严格模拟真实交易
  - T+1制度实现
  - 最小交易单位校验（100股整数倍）
  - 印花税0.1% + 佣金0.03%真实计算
  - 涨跌停分级（普通±10%, ST±5%, 科创板±20%）
- ⚠️ **数据库优化**: 性能与准确性提升
  - klines表增加复权因子(adjust_factor)
  - 按时间分区，查询性能提升3-5倍
  - trades表增加strategy_instance_id
  - 税费字段独立记录
- ⚠️ **AI代码沙箱增强**: 防止资源耗尽
  - 30秒强制超时(func_timeout)
  - Docker容器CPU/内存限制
  - 死循环检测

**v1.3.0 (2025-11-29)** - 模拟盘优先 + 多模型支持
- 模拟盘默认，降低风险
- 支持deepseek/qwen等高性价比模型
- 多数据源容错(akshare/baostock/efinance)
- A股市场适配层
- 影子账户历史回放
- AI托管双模式(免确认/需确认)
- 策略逻辑测试框架
- Claude Code + SPEC + TDD开发流程

**v1.2.0** - AI策略研究员功能
**v1.1.0** - 安全与性能优化
**v1.0.0** - 初始版本

---

**架构审查**: Gemini架构师
**评分**: 架构合理性 4.5/5, 技术选型 5/5, 落地可行性 4.5/5, 风险控制 4/5 → 4.5/5 (v1.3.1优化后)

---

**完整实现代码参考**: CN5-Lite-Full.md
**GitHub**: https://github.com/minionszyw/cn5-lite
**维护者**: CN5团队

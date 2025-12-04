# CN5-Lite 架构设计文档

## 📋 概述

CN5-Lite是一个轻量级AI驱动的量化交易系统，采用模块化架构，严格遵循TDD开发模式。

**版本**: 1.0.0
**最后更新**: 2025-11-30

---

## 🏗️ 系统架构

### 分层架构

```
┌─────────────────────────────────────────┐
│         UI Layer (Streamlit)            │  用户界面层
├─────────────────────────────────────────┤
│      API Layer (FastAPI)                │  API接口层
├─────────────────────────────────────────┤
│      Service Layer                      │  业务逻辑层
│  ┌──────┬──────┬──────┬──────┬──────┐  │
│  │AI生成│回测  │交易  │影子  │风控  │  │
│  └──────┴──────┴──────┴──────┴──────┘  │
├─────────────────────────────────────────┤
│      Data Layer                         │  数据访问层
│  ┌──────────┬──────────┐               │
│  │ SQLite   │多数据源  │               │
│  └──────────┴──────────┘               │
└─────────────────────────────────────────┘
```

### 核心模块

#### 1. AI策略生成器 (ai_generator.py)

**职责**: 将自然语言转换为可执行策略代码

**组件**:
- `AIClient`: OpenAI API封装
- `CodeSecurityChecker`: 代码安全验证
- `StrategySandbox`: 沙箱执行环境
- `StrategyStorage`: 数据库持久化
- `StrategyValidator`: 逻辑测试

**流程**:
```
用户输入 → AI生成代码 → 安全检查 → 沙箱测试 → 保存数据库
```

#### 2. 策略适配器 (strategy_adapter.py)

**职责**: 消除回测/实盘代码鸿沟

**设计模式**: 适配器模式

**关键功能**:
- T+1锁定机制
- 状态持久化
- 防未来函数

**原理**:
```python
# 统一接口
class StandardStrategy:
    def on_bar(self, bar): ...

# 适配器包装
adapter = StrategyAdapter(code)
signal = adapter.process_bar(bar)  # 自动处理T+1
```

#### 3. 回测引擎 (backtest_engine.py)

**职责**: 执行策略回测，模拟A股市场

**A股规则** (8条):
1. 停牌检测
2. 涨跌停限制
3. T+1制度
4. 最小交易单位
5. 印花税
6. 佣金
7. 滑点
8. 仓位/资金管理

**性能指标**:
- 年化收益率
- 夏普比率
- 最大回撤
- 胜率
- 波动率

#### 4. 风控验证器 (risk_validator.py)

**职责**: 7层风控防护

**7层架构**:
```
1. 总资金止损 (10%)  ─┐
2. 黑名单股票        │
3. 单日亏损 (5%)     ├─→ 逐层验证
4. 单策略资金 (30%)  │
5. 单笔限制 (20%)    │
6. 交易频率          │
7. 涨跌停检测        ─┘
```

**风险评分**: 0-100分，综合各层风险

#### 5. 影子账户管理器 (shadow_manager.py)

**职责**: 策略评分与晋升

**5维度评分**:
```
总分 = Σ(归一化[指标] × 权重)

指标         权重
年化收益率   30%
夏普比率     25%
最大回撤     20%
波动率       15%
胜率         10%
```

**时间衰减**: 指数衰减，半衰期7天

**晋升条件**:
- 得分 ≥ 35
- 观察 ≥ 14天

#### 6. AI交易管理器 (ai_trading_manager.py)

**职责**: 自动交易执行

**关键特性**:
- 双确认模式（免确认/需确认）
- 断点续传（容器重启恢复）
- 逻辑测试框架

**断点续传机制**:
```
1. 从trades表恢复持仓
2. 重放历史K线恢复指标
3. 恢复T+1锁定
```

#### 7. 多数据源管理器 (multi_datasource.py)

**职责**: 数据获取与归一化

**容错机制**:
```
AkShare (优先) → Baostock → Efinance
```

**归一化处理**:
- 统一列名
- 统一复权方式
- 填充缺失值
- OHLC校验
- 异常值过滤

---

## 🔄 数据流

### 策略完整生命周期

```
┌─────────────┐
│ AI生成策略   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 安全验证     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 回测验证     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 影子账户     │ ← 7-14天观察
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 评分晋升     │ ← 得分≥35
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 自动交易     │ ← 实盘运行
└─────────────┘
```

### 交易执行流程

```
策略信号 → 风控验证 → 执行交易 → 记录DB → 状态更新
    ↑          │          │
    │          ▼          ▼
    └──── T+1锁定 ← 持仓管理
```

---

## 🗄️ 数据库设计

### ER图

```
┌─────────────┐
│ strategies  │
│ (策略表)    │
└──────┬──────┘
       │ 1
       │
       │ N
       ▼
┌─────────────┐     ┌──────────────┐
│backtest_    │ N:1 │shadow_       │
│results      │────→│accounts      │
└─────────────┘     └──────────────┘
       │                    │
       │ N                  │ N
       ▼                    ▼
┌─────────────────────────────┐
│         trades              │
│       (交易记录)            │
└─────────────────────────────┘
```

### 核心表

**strategies** - 策略表
```sql
CREATE TABLE strategies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    params JSON,
    status TEXT,  -- draft/shadow/live
    annual_return REAL,
    sharpe_ratio REAL,
    created_at TIMESTAMP
);
```

**trades** - 交易记录表
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    strategy_id INTEGER,
    symbol TEXT,
    action TEXT,  -- buy/sell
    price REAL,
    volume INTEGER,
    commission REAL,
    tax REAL,
    pnl REAL,
    trade_time TIMESTAMP
);
```

---

## 🔐 安全设计

### 代码安全

**多层检查**:
1. AST语法解析
2. 危险函数黑名单
3. 圈复杂度限制
4. 沙箱执行
5. 超时保护

**黑名单**:
- 系统模块: os, sys, subprocess
- 危险函数: eval, exec, compile, open
- 网络模块: socket, urllib, requests

### 数据安全

**敏感数据过滤**:
```python
# 日志中自动脱敏
API_KEY: sk-abc*** (隐藏后8位)
```

**SQL注入防护**:
```python
# 使用参数化查询
cursor.execute("SELECT * FROM strategies WHERE id=?", (strategy_id,))
```

---

## ⚡ 性能优化

### 数据库优化

**索引策略**:
```sql
CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_trades_date ON trades(trade_time);
```

**WAL模式**:
```sql
PRAGMA journal_mode=WAL;  -- 并发性能提升
```

### 代码优化

**缓存策略**:
```python
@lru_cache(maxsize=128)
def get_strategy(strategy_id):
    # 缓存热门策略
    pass
```

**批量处理**:
```python
# 批量插入而非逐条
cursor.executemany("INSERT INTO trades VALUES (?, ?, ?)", trades_batch)
```

---

## 🧪 测试架构

### 测试金字塔

```
        /\
       /集\
      /成测\
     /试  \
    /────────\
   / 单元测试  \
  /____________\
```

**测试覆盖**:
- 单元测试: 200+ 测试用例
- 集成测试: 59 测试用例
- 覆盖率: 80%+

### TDD流程

```
1. Red   → 编写失败的测试
2. Green → 实现最小代码使测试通过
3. Refactor → 重构优化
```

---

## 🔄 扩展性设计

### 插件式架构

**数据源插件**:
```python
class DataSourceProvider(ABC):
    @abstractmethod
    def fetch(self, symbol, start, end):
        pass

# 新增数据源只需实现接口
class NewDataSource(DataSourceProvider):
    def fetch(self, symbol, start, end):
        # 实现
        pass
```

**策略插件**:
```python
# 用户自定义策略只需实现on_bar
class UserStrategy:
    def on_bar(self, bar):
        # 自定义逻辑
        return signal
```

### 配置化设计

**环境变量配置**:
```bash
# 所有关键参数都可配置
MAX_TOTAL_LOSS_RATE=0.10
AI_TIMEOUT=180
DATA_SOURCE_PRIORITY=akshare,baostock
```

---

## 🚀 部署架构

### 单机部署

```
┌─────────────────────────────┐
│      Nginx (反向代理)        │
└──────────┬──────────────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌────────┐  ┌────────┐
│FastAPI │  │Streamlit│
└────┬───┘  └────────┘
     │
     ▼
┌────────┐
│SQLite  │
└────────┘
```

### Docker部署

```
┌─────────────────────────────┐
│   Docker Compose            │
│  ┌──────┐  ┌──────┐        │
│  │ API  │  │  UI  │        │
│  └──┬───┘  └──────┘        │
│     │                       │
│  ┌──▼───┐                  │
│  │SQLite│                  │
│  └──────┘                  │
└─────────────────────────────┘
```

---

## 📊 监控设计

### 关键指标

**系统指标**:
- CPU使用率
- 内存使用率
- API响应时间
- 数据库连接数

**业务指标**:
- 策略数量
- 交易次数
- 风控拦截率
- 平均收益率

### 日志设计

**分级日志**:
- DEBUG: 调试信息
- INFO: 常规信息
- WARNING: 警告
- ERROR: 错误

**日志格式**:
```
2024-01-01 10:00:00 | INFO | module | message
```

---

## 🔮 未来规划

### 短期（1-3月）

- [ ] WebSocket实时推送
- [ ] 更多技术指标
- [ ] 策略回放功能
- [ ] 性能仪表板

### 中期（3-6月）

- [ ] 多账户管理
- [ ] 社区策略市场
- [ ] 机器学习优化
- [ ] 移动端App

### 长期（6-12月）

- [ ] 分布式回测
- [ ] 云端部署
- [ ] 期货/期权支持
- [ ] 多市场支持

---

## 📚 参考资料

- **设计模式**: [Design Patterns](https://refactoring.guru/design-patterns)
- **FastAPI**: [FastAPI Docs](https://fastapi.tiangolo.com/)
- **SQLite**: [SQLite Docs](https://www.sqlite.org/docs.html)
- **量化交易**: [QuantStart](https://www.quantstart.com/)

---

**文档维护者**: CN5-Lite团队
**最后审查**: 2025-11-30

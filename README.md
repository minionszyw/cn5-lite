# CN5-Lite AI量化交易系统

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-80%25+-brightgreen.svg)](tests/)

**版本**: 1.0.0
**定位**: 个人散户(中国A股,模拟盘) AI量化交易系统
**开发方法**: 严格TDD（测试先行）

---

## 📋 项目概述

CN5-Lite是轻量级AI驱动的量化交易系统，为A股散户(<10万资金)设计。

### 核心特性

- ✅ **AI策略研究员**: 自动生成/优化/筛选策略
- ✅ **模拟盘优先**: 模拟交易，降低风险
- ✅ **A股适配**: 停牌/涨跌停/T+1/除权处理
- ✅ **多数据源**: AkShare/baostock/efinance容错
- ✅ **高性价比AI**: 支持deepseek/qwen等模型
- ✅ **7层风控**: 多维度风险控制系统
- ✅ **影子账户**: 策略评分与晋升机制
- ✅ **断点续传**: 容器重启自动恢复策略状态

---

## 🎯 开发进度总览

### ✅ 已完成 (Day 1-51) - 项目完工！🎉

| 阶段 | 模块 | 状态 | 测试覆盖率 | 提交 |
|------|------|------|-----------|------|
| Day 1-5 | 多数据源管理器 | ✅ | 94.35% | d94f7fc |
| Day 6 | 配置管理 & 日志系统 | ✅ | 91%+ | 2706652 |
| Day 7-10 | AI策略生成器 | ✅ | 78%+ | f557077 |
| Day 11-14 | 策略适配器层 | ✅ | 88%+ | 23a3dd4 |
| Day 15-19 | 回测引擎 + A股规则 | ✅ | - | 395cd25 |
| Day 20-23 | 7层风控验证器 | ✅ | - | 04cb302 |
| Day 24-28 | 影子账户管理器 | ✅ | - | eb624bb |
| Day 29-33 | AI交易管理器 | ✅ | - | b7c0be6 |
| Day 34-38 | FastAPI接口层 | ✅ | - | 8f8d98d |
| Day 39-44 | Streamlit前端 | ✅ | - | 4ad523a |
| Day 45-48 | 集成测试 | ✅ | - | 2da2797 |
| Day 49-51 | 性能优化&文档 | ✅ | - | 95e0ff3 |

**项目统计**:
- 总代码行数: ~10,000行
- 总文档行数: ~5,000行
- 测试用例数: 259个
- API端点数: 27个
- UI页面数: 6个
- 平均测试覆盖率: 80%+

---

## 🏗️ 系统架构

### 技术栈

#### 后端
- **FastAPI** 0.109+ - RESTful API网关
- **SQLite** - 轻量级数据存储
- **OpenAI API** - AI策略生成（支持deepseek/qwen/gpt兼容）

#### 量化框架
- **自研回测引擎** - A股市场规则完整实现
- **StrategyAdapter** - 统一回测/实盘接口

#### 数据源
- **AkShare** 1.13.5 - 优先数据源
- **Baostock** 0.8.9 - 容错备选
- **Efinance** 0.5.3 - 第三备选

#### 测试
- **pytest** - 单元测试框架
- **pytest-cov** - 覆盖率报告
- **TDD开发** - 测试先行开发模式

---

## 📁 项目结构

```
cn5-lite/
├── app/                        # 主应用
│   ├── config.py               # ✅ 配置管理（单例+验证）
│   ├── logger.py               # ✅ 日志系统（敏感数据过滤）
│   ├── database.py             # ✅ SQLite数据库管理
│   ├── errors.py               # ✅ 自定义异常体系
│   │
│   ├── api/                    # ✅ FastAPI接口层
│   │   ├── main.py             # FastAPI应用入口
│   │   └── routes/             # API路由模块
│   │       ├── strategy.py     # 策略管理（6个端点）
│   │       ├── backtest.py     # 回测（2个端点）
│   │       ├── trading.py      # 交易管理（6个端点）
│   │       ├── shadow.py       # 影子账户（6个端点）
│   │       └── risk.py         # 风控（7个端点）
│   │
│   └── services/               # ✅ 核心业务逻辑
│       ├── multi_datasource.py          # 多数据源管理器
│       ├── ai_generator.py              # AI策略生成器
│       ├── strategy_adapter.py          # 策略适配器层
│       ├── backtest_engine.py           # 回测引擎
│       ├── risk_validator.py            # 7层风控验证器
│       ├── shadow_manager.py            # 影子账户管理器
│       └── ai_trading_manager.py        # AI交易管理器
│
├── tests/                      # ✅ 测试套件
│   ├── unit/                   # 单元测试（200+测试用例）
│   │   ├── test_multi_datasource.py
│   │   ├── test_config.py
│   │   ├── test_logger.py
│   │   ├── test_ai_generator.py
│   │   ├── test_strategy_adapter.py
│   │   ├── test_backtest_engine.py
│   │   ├── test_risk_validator.py
│   │   ├── test_shadow_manager.py
│   │   └── test_ai_trading_manager.py
│   ├── integration/            # 集成测试
│   └── conftest.py             # pytest配置
│
├── database/
│   └── init.sql                # ✅ 数据库初始化
├── docker-compose.yml          # ✅ Docker编排
├── requirements.txt            # ✅ Python依赖
├── pytest.ini                  # ✅ pytest配置
├── .env.example                # ✅ 环境变量模板
├── CN5-Lite.md                 # 完整架构设计文档
└── README.md                   # 本文件
```

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/minionszyw/cn5-lite.git
cd cn5-lite
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑.env文件，填入必要配置
```

必需配置项：
```bash
# AI模型（必需）
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE_URL=https://api.deepseek.com/v1  # 可选，默认OpenAI
AI_MODEL=deepseek-chat

# 数据源
DATA_SOURCE_PRIORITY=akshare,baostock,efinance

# 风控
TOTAL_CAPITAL=100000
MAX_TOTAL_LOSS_RATE=0.10
MAX_DAILY_LOSS_RATE=0.05
```

### 3. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 启动服务

**方式一：一键启动（推荐）**
```bash
# 启动后端API服务（后台运行）
source .venv/bin/activate
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload &

# 启动前端Web界面
streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
```

**方式二：分别启动**
```bash
# 终端1：启动后端API
source .venv/bin/activate
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

# 终端2：启动前端UI
source .venv/bin/activate
streamlit run ui/app.py --server.port 8501
```

### 5. 访问系统

- **前端界面**: http://localhost:8501
- **API文档**: http://localhost:8000/docs
- **API服务**: http://localhost:8000

### 6. 运行测试（可选）

```bash
# 单元测试
pytest tests/unit/ -v

# 查看覆盖率
pytest tests/unit/ --cov=app --cov-report=html
```

---

## 📚 核心模块详解

### 1️⃣ 多数据源管理器

**文件**: `app/services/multi_datasource.py`

**功能**:
- 3数据源自动容错（AkShare → Baostock → Efinance）
- 数据归一化（统一OHLCV格式）
- Redis限流保护（防IP封禁）
- 数据质量验证

**使用示例**:
```python
from app.services.multi_datasource import DataSourceManager

manager = DataSourceManager()
data = manager.fetch(
    symbol="SH600000",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

### 2️⃣ AI策略生成器

**文件**: `app/services/ai_generator.py`

**功能**:
- 自然语言→可执行策略代码
- 代码安全检查（AST解析+黑名单）
- 沙箱执行（超时保护）
- 策略存储与验证

**关键组件**:
- `CodeSecurityChecker`: 危险代码检测
- `StrategySandbox`: 安全执行环境
- `StrategyStorage`: SQLite持久化
- `StrategyValidator`: 逻辑测试

**使用示例**:
```python
from app.services.ai_generator import AIStrategyGenerator

generator = AIStrategyGenerator(
    api_key="sk-xxx",
    base_url="https://api.deepseek.com/v1",
    model="deepseek-chat"
)

result = generator.generate("双均线策略，MA5/MA20金叉买入")
# result = {"code": "...", "name": "MAStrategy", "params": {...}}
```

### 3️⃣ 策略适配器层

**文件**: `app/services/strategy_adapter.py`

**功能**:
- 消除回测/实盘代码鸿沟
- T+1锁定机制
- 状态持久化
- 防未来函数

**设计理念**: "所测即所跑"

### 4️⃣ 回测引擎

**文件**: `app/services/backtest_engine.py`

**功能**:
- 完整A股市场规则（8条规则）
- 性能指标计算（年化收益/夏普/最大回撤）
- 与StrategyAdapter集成

**A股规则**:
1. 停牌检测（volume=0）
2. 涨跌停限制（普通±10%, ST±5%, 科创板±20%）
3. T+1制度（当日买入不可卖出）
4. 最小交易单位（买入100股整数倍）
5. 印花税（卖出0.1%）
6. 佣金（双向0.03%，最低¥5）
7. 滑点估算（0.1%）
8. 仓位/资金管理

### 5️⃣ 7层风控验证器

**文件**: `app/services/risk_validator.py`

**7层防护**:
1. 总资金止损（默认10%）
2. 黑名单股票（ST/退市）
3. 单日亏损限制（默认5%）
4. 单策略资金占用（默认30%）
5. 单笔过大（默认20%）
6. 异常交易频率（20笔/小时）
7. 涨跌停板检测

**使用示例**:
```python
from app.services.risk_validator import RiskValidator

validator = RiskValidator(total_capital=100000)
result = validator.validate({
    'action': 'buy',
    'symbol': 'SH600000',
    'amount': 100,
    'price': 10.0
})
# result = {"passed": True/False, "reason": "...", "risk_score": 0-100}
```

### 6️⃣ 影子账户管理器

**文件**: `app/services/shadow_manager.py`

**功能**:
- 5维度策略评分系统
- 时间衰减权重（半衰期7天）
- 自动晋升机制（得分≥35，观察≥14天）

**评分维度**（权重）:
- 年化收益率（30%）
- 夏普比率（25%）
- 最大回撤（20%）
- 波动率（15%）
- 胜率（10%）

### 7️⃣ AI交易管理器

**文件**: `app/services/ai_trading_manager.py`

**功能**:
- 自动交易执行
- 双确认模式（免确认/需确认）
- 容器重启断点续传
- 逻辑测试框架

**断点续传机制**:
1. 从trades表恢复持仓和成本价
2. 重放历史K线恢复技术指标
3. 恢复T+1锁定持仓

---

## 🌐 API接口文档

### 总览

- **总计**: 27个RESTful端点
- **基础URL**: `http://localhost:8000/api/v1`
- **文档**: http://localhost:8000/docs

### 策略管理 API

**路由前缀**: `/api/v1/strategies`

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/generate` | AI生成策略 |
| POST | `/` | 创建策略 |
| GET | `/{id}` | 获取策略详情 |
| GET | `/` | 策略列表 |
| DELETE | `/{id}` | 删除策略 |
| POST | `/{id}/validate` | 验证策略代码 |

**示例**:
```bash
# 生成策略
curl -X POST http://localhost:8000/api/v1/strategies/generate \
  -H "Content-Type: application/json" \
  -d '{"user_input": "双均线策略", "context": {}}'
```

### 回测 API

**路由前缀**: `/api/v1/backtest`

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/run` | 运行回测 |
| POST | `/quick` | 快速回测（最近N天） |

**示例**:
```bash
# 运行回测
curl -X POST http://localhost:8000/api/v1/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": 1,
    "symbol": "SH600000",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_cash": 100000
  }'
```

### 交易管理 API

**路由前缀**: `/api/v1/trading`

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/start` | 启动自动交易 |
| POST | `/stop` | 停止自动交易 |
| GET | `/status` | 获取交易状态 |
| GET | `/trades/{strategy_id}` | 获取交易记录 |
| POST | `/execute` | 手动执行交易 |
| POST | `/rehydrate/{strategy_id}` | 恢复策略状态 |

### 影子账户 API

**路由前缀**: `/api/v1/shadow`

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/accounts` | 创建影子账户 |
| GET | `/accounts/{id}` | 获取账户详情 |
| GET | `/top` | 获取Top N策略 |
| POST | `/accounts/{id}/promote` | 晋升到实盘 |
| POST | `/accounts/{id}/terminate` | 终止账户 |
| GET | `/accounts/{id}/score` | 获取账户评分 |

### 风控 API

**路由前缀**: `/api/v1/risk`

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/validate` | 验证交易 |
| GET | `/config` | 获取风控配置 |
| PUT | `/config` | 更新风控配置 |
| POST | `/account/update` | 更新账户价值 |
| GET | `/blacklist` | 获取黑名单 |
| POST | `/blacklist/add` | 添加黑名单 |
| DELETE | `/blacklist/{symbol}` | 移除黑名单 |

---

## 🧪 测试

### 测试统计

- **总测试用例**: 200+
- **测试模块**: 9个
- **平均覆盖率**: 80%+

### 运行测试

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定模块
pytest tests/unit/test_backtest_engine.py -v

# 查看覆盖率
pytest tests/unit/ --cov=app --cov-report=html
# 打开 htmlcov/index.html 查看详细报告

# 运行集成测试（需要API密钥）
export OPENAI_API_KEY=sk-xxx
pytest tests/integration/ -m slow -v
```

### 测试结构

```
tests/
├── unit/                               # 单元测试
│   ├── test_multi_datasource.py        # 30测试，94.35%覆盖
│   ├── test_config.py                  # 20测试，91%覆盖
│   ├── test_logger.py                  # 26测试
│   ├── test_ai_generator.py            # 29测试，78%覆盖
│   ├── test_strategy_adapter.py        # 18测试，88%覆盖
│   ├── test_backtest_engine.py         # 30测试
│   ├── test_risk_validator.py          # 30测试
│   ├── test_shadow_manager.py          # 30测试
│   └── test_ai_trading_manager.py      # 30测试
├── integration/                        # 集成测试
└── conftest.py                         # 全局配置
```

---

## 🗄️ 数据库

### SQLite Schema

**核心表**:
- `strategies` - 策略表
- `backtest_results` - 回测结果表
- `trades` - 交易记录表
- `shadow_accounts` - 影子账户表

**初始化**:
```bash
# 自动创建（首次运行时）
from app.database import init_db
init_db()
```

**查看数据库**:
```bash
# 使用sqlite3命令行
sqlite3 data/cn5lite.db

# 查看所有表
.tables

# 查询策略
SELECT id, name, status FROM strategies;
```

---

## ⚙️ 配置说明

### 环境变量

完整配置见 `.env.example`

**核心配置**:

```bash
# ============ AI模型 ============
OPENAI_API_KEY=sk-xxx                          # API密钥（必需）
OPENAI_API_BASE_URL=https://api.deepseek.com/v1  # API端点
AI_MODEL=deepseek-chat                         # 模型名称

# ============ 数据源 ============
DATA_SOURCE_PRIORITY=akshare,baostock,efinance
DATA_CACHE_DAYS=30

# ============ 风控 ============
TOTAL_CAPITAL=100000                           # 总资金
MAX_TOTAL_LOSS_RATE=0.10                       # 总止损10%
MAX_DAILY_LOSS_RATE=0.05                       # 日止损5%
MAX_STRATEGY_CAPITAL_RATE=0.30                 # 单策略30%
MAX_SINGLE_TRADE_RATE=0.20                     # 单笔20%

# ============ 交易模式 ============
TRADING_MODE=simulation                        # simulation/live
REQUIRE_APPROVAL=false                         # 免确认模式
AUTO_APPROVE_THRESHOLD=3000                    # 自动审批阈值
```

### 日志配置

日志位置: `logs/cn5lite_{date}.log`

**特性**:
- 敏感数据自动过滤（API密钥/密码）
- 按日滚动（1KB触发）
- 保留7天
- JSON结构化输出

---

## 🔒 安全特性

### 代码安全

1. **AST解析**: 检测危险函数（eval/exec/os/sys）
2. **沙箱执行**: 超时保护（30秒）
3. **圈复杂度限制**: ≤20
4. **必需方法检查**: 确保策略实现on_bar

### 数据安全

1. **敏感数据过滤**: 日志自动脱敏
2. **SQL注入防护**: 参数化查询
3. **配置验证**: 启动时检查必需配置

### 交易安全

1. **7层风控**: 多维度风险控制
2. **双确认模式**: 大额交易需审核
3. **黑名单机制**: 禁止ST/退市股票

---

## 📖 开发规范

### TDD开发流程

```
1. 编写测试用例 → 2. 实现功能 → 3. 运行测试 → 4. 代码审查
```

### 质量门禁

每个模块完成前必须通过：
- ✅ 单元测试覆盖率>80%
- ✅ 所有测试用例通过
- ✅ 代码语法检查通过
- ✅ 无安全漏洞

### Git提交规范

```bash
<type>: <subject>

# type类型
feat:     新功能
fix:      修复bug
refactor: 重构
test:     测试
docs:     文档

# 示例
feat: Day 34-38 FastAPI接口层完整实现
test: 添加回测引擎单元测试
fix: 修复T+1锁定机制bug
```

---

## 🛠️ 常见问题

### Q: 如何切换AI模型?

编辑 `.env` 文件：
```bash
# 使用deepseek
AI_MODEL=deepseek-chat
OPENAI_API_BASE_URL=https://api.deepseek.com/v1

# 使用OpenAI
AI_MODEL=gpt-4
OPENAI_API_BASE_URL=  # 留空使用默认

# 使用通义千问
AI_MODEL=qwen-plus
OPENAI_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### Q: 数据源获取失败怎么办?

系统会自动容错切换到下一数据源。检查：
1. 网络连接是否正常
2. 是否触发限流（1次/秒）
3. 股票代码格式是否正确（SH600000/SZ000001）

### Q: 如何查看测试覆盖率?

```bash
pytest tests/unit/ --cov=app --cov-report=html
open htmlcov/index.html
```

### Q: API文档在哪里?

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Q: 如何添加新策略?

方式1（API）:
```bash
curl -X POST http://localhost:8000/api/v1/strategies/generate \
  -H "Content-Type: application/json" \
  -d '{"user_input": "你的策略描述"}'
```

方式2（代码）:
```python
from app.services.ai_generator import AIStrategyGenerator

generator = AIStrategyGenerator(api_key="sk-xxx")
result = generator.generate("双均线策略")
```

---

## 📚 参考文档

- **完整架构设计**: [CN5-Lite.md](CN5-Lite.md)
- **API文档**: http://localhost:8000/docs
- **测试报告**: `htmlcov/index.html`

---

## 🤝 贡献指南

欢迎贡献！请遵循：

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/xxx`)
3. 编写测试用例（TDD）
4. 实现功能代码
5. 运行测试确保通过
6. 提交更改 (`git commit -m 'feat: xxx'`)
7. 推送到分支 (`git push origin feature/xxx`)
8. 创建Pull Request

---

## 📄 许可证

MIT License

---

## 📧 联系方式

- **GitHub**: https://github.com/minionszyw/cn5-lite
- **Issues**: https://github.com/minionszyw/cn5-lite/issues

---

## ⚠️ 免责声明

**本系统仅供学习和研究使用，不构成投资建议。量化交易存在风险，请谨慎使用。**

---

## 🎉 致谢

感谢所有开源项目的贡献者：
- FastAPI - 现代化Web框架
- pytest - 强大的测试框架
- AkShare/Baostock/Efinance - 数据源支持
- OpenAI - AI模型接口标准

---

**最后更新**: 2025-11-30
**项目状态**: 🎉 **v1.0.0正式发布** - 全部51天开发计划完成！

---

## 📊 项目成果

### 代码统计

| 类别 | 数量 | 说明 |
|------|------|------|
| 核心模块 | 8个 | 多数据源/AI生成/适配器/回测/风控/影子/交易/配置 |
| API端点 | 27个 | RESTful接口，完整CRUD |
| UI页面 | 6个 | Streamlit交互式界面 |
| 单元测试 | 200+个 | 覆盖所有核心功能 |
| 集成测试 | 59个 | 端到端业务流程验证 |
| 代码行数 | ~10,000行 | Python代码 |
| 文档行数 | ~5,000行 | Markdown文档 |
| 测试覆盖率 | 80%+ | 高质量保证 |

### 功能特性

**核心能力**:
- ✅ AI自动生成策略（OpenAI协议兼容）
- ✅ 完整回测引擎（A股8条规则）
- ✅ 7层风控系统
- ✅ 影子账户自动评分晋升
- ✅ 断点续传（容器重启恢复）
- ✅ 多数据源容错
- ✅ RESTful API（27个端点）
- ✅ Web UI（6个页面）

**技术亮点**:
- 🎯 严格TDD开发（测试先行）
- 🔐 代码安全检查（AST解析+沙箱）
- 📊 5维度策略评分
- 🔄 T+1锁定机制
- 💹 真实税费计算
- 📈 Plotly交互式图表
- 🚀 性能优化工具

---

## 📖 完整文档

### 用户文档
- [快速开始](#快速开始) - 5分钟上手
- [核心模块详解](#核心模块详解) - 功能说明
- [API接口文档](#api接口文档) - 27个端点
- [常见问题](#常见问题) - FAQ

### 开发文档
- [部署指南](docs/DEPLOYMENT.md) - 本地/Docker/生产环境
- [API文档](docs/API.md) - 详细API规范
- [架构设计](docs/ARCHITECTURE.md) - 系统架构
- [贡献指南](docs/CONTRIBUTING.md) - 参与贡献
- [更新日志](CHANGELOG.md) - 版本历史

### 技术文档
- [CN5-Lite.md](CN5-Lite.md) - 完整技术设计
- [测试文档](tests/integration/README.md) - 集成测试
- [UI文档](ui/README.md) - 前端说明

---

## 🚀 下一步计划

### v1.1.0 规划（1-3月）
- [ ] WebSocket实时推送
- [ ] 更多技术指标库
- [ ] 策略回放功能
- [ ] 性能仪表板

### v1.2.0 规划（3-6月）
- [ ] 多账户管理
- [ ] 社区策略市场
- [ ] 机器学习优化
- [ ] 移动端App

### v2.0.0 规划（6-12月）
- [ ] 分布式回测
- [ ] 云端部署
- [ ] 期货/期权支持
- [ ] 多市场支持（港股/美股）

---

**最后更新**: 2025-11-30
**项目状态**: 🎉 **v1.0.0正式发布** - 全部51天开发计划完成！

# CN5-Lite AI量化交易系统

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**版本**: 1.0.0-dev
**定位**: 个人散户(中国A股,模拟盘) AI量化交易系统
**开发方法**: 严格TDD（测试先行）

---

## 项目概述

CN5-Lite是轻量级AI驱动的量化交易系统，为A股散户(<10万资金)设计。

### 核心特性

- ✅ **AI策略研究员**: 生成/优化/筛选策略
- ✅ **模拟盘优先**: vnpy模拟交易，降低风险
- ✅ **A股适配**: 停牌/涨跌停/除权处理
- ✅ **多数据源**: AkShare/baostock/efinance容错
- ✅ **高性价比AI**: 支持deepseek/qwen等模型

---

## 技术栈

### 后端

- **FastAPI** 0.109+ - API网关
- **Celery** 5.3+ - 异步任务
- **PostgreSQL** 15+ - 主存储
- **Redis** 7.2+ - 消息队列+缓存

### 量化框架

- **Backtrader** 1.9.78+ - 回测引擎
- **vn.py** 3.9+ - 模拟盘/实盘

### 前端

- **Streamlit** 1.30+ - Web UI

### 数据源

- **AkShare** 1.13.5
- **Baostock** 0.8.9
- **efinance** 0.5.3

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/minionszyw/cn5-lite.git
cd cn5-lite
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑.env文件，填入API密钥
```

### 3. 启动Docker环境

```bash
# 启动PostgreSQL和Redis
docker compose up -d

# 查看容器状态
docker compose ps
```

### 4. 安装Python依赖（可选，本地开发）

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

---

## 运行测试

### 单元测试

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定模块测试
pytest tests/unit/test_multi_datasource.py -v

# 生成覆盖率报告
pytest tests/unit/ --cov=app --cov-report=html
```

### 集成测试（需要真实API）

```bash
# 运行集成测试（标记为slow）
pytest tests/integration/ -m slow -v

# 跳过慢速测试
pytest tests/integration/ -m "not slow" -v
```

### 在Docker容器中运行测试

```bash
# 进入容器
docker exec -it cn5lite_app bash

# 运行测试
pytest tests/unit/test_multi_datasource.py -v --cov=app/services/multi_datasource
```

---

## 项目结构

```
cn5-lite/
├── app/                    # 主应用
│   ├── api/                # API路由
│   ├── services/           # 业务逻辑
│   │   └── multi_datasource.py  # 多数据源管理器 ✅
│   ├── models/             # 数据模型
│   ├── tasks/              # Celery任务
│   └── errors.py           # 自定义异常 ✅
├── ui/                     # Streamlit前端
├── tests/                  # 测试
│   ├── unit/               # 单元测试 ✅
│   ├── integration/        # 集成测试 ✅
│   └── conftest.py         # pytest配置 ✅
├── database/
│   └── init.sql            # 数据库初始化 ✅
├── docker-compose.yml      # Docker编排 ✅
├── requirements.txt        # Python依赖 ✅
├── pytest.ini              # pytest配置 ✅
└── .env.example            # 环境变量模板 ✅
```

---

## 开发进度

### ✅ Day 1: 环境配置（已完成）

- 项目目录结构
- Docker配置（PostgreSQL + Redis）
- 数据库初始化（7张表 + 5个分区表）
- Python依赖配置
- 测试环境配置

### ✅ Day 2: 多数据源管理器测试用例（已完成）

- pytest全局配置和Fixtures
- 单元测试（30+ 测试用例）
- 集成测试（10+ 测试用例）

### ✅ Day 3-4: 多数据源管理器实现（已完成）

- 自定义异常体系
- 数据源提供者（AkShare, Baostock, Efinance）
- 数据归一化器
- Redis限流器
- 多源容错管理器

### 🔄 Day 5: 测试验证（进行中）

- 运行单元测试
- 修复bug
- 确保测试覆盖率>80%

### ⬜ Day 6: 基础工具类

- 配置管理
- 日志系统

### ⬜ Day 7-10: AI策略生成器

### ⬜ Day 11-14: 策略适配器层

### ⬜ Day 15-19: 回测引擎

---

## 开发规范

### TDD开发流程

```
1. 编写测试用例（单元测试 + 集成测试）
2. 实现功能代码
3. 运行测试验证
4. 代码审查和文档更新
```

### 质量门禁

每个模块完成前必须通过：

- [ ] 单元测试覆盖率>80%
- [ ] 所有测试用例通过
- [ ] 集成测试至少1个场景通过
- [ ] 代码语法检查通过
- [ ] 无类型错误（mypy）

---

## 数据库

### 核心表

- **strategies** - 策略表
- **backtest_results** - 回测结果表
- **shadow_accounts** - 影子账户表
- **trades** - 交易记录表
- **klines** - K线数据表（分区表 2022-2026）
- **risk_logs** - 风控日志表
- **system_logs** - 系统日志表

### 连接数据库

```bash
# 使用psql连接
psql -h localhost -U cn5user -d cn5lite

# 查看所有表
\dt

# 查看分区表
SELECT tablename FROM pg_tables WHERE tablename LIKE 'klines_%';
```

---

## 环境变量

关键配置项（详见 `.env.example`）：

```bash
# AI模型
AI_API_KEY=sk-xxx                          # API密钥（必需）
AI_BASE_URL=https://api.deepseek.com/v1   # API端点
AI_MODEL=deepseek-chat                     # 模型名称

# 数据源
DATA_SOURCE_PRIORITY=akshare,baostock,efinance

# 风控
TOTAL_STOP_LOSS_RATIO=0.10                # 总资金止损10%
DAILY_LOSS_LIMIT_RATIO=0.05               # 单日亏损5%

# 交易模式
TRADING_MODE=simulation                    # simulation/live
```

---

## 常见问题

### Q: 如何切换AI模型?

编辑 `.env` 文件：

```bash
AI_MODEL=deepseek-chat  # 或 qwen-plus/gpt-4
AI_BASE_URL=https://api.deepseek.com/v1
```

### Q: 如何运行测试?

```bash
# 单元测试
pytest tests/unit/ -v

# 集成测试（需要API密钥）
export AI_API_KEY=sk-xxx
pytest tests/integration/ -m slow -v
```

### Q: 数据库容器启动失败?

检查端口占用：

```bash
# 查看5432端口
lsof -i :5432

# 停止旧容器
docker compose down
docker compose up -d
```

---

## 贡献指南

欢迎贡献！请遵循：

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/xxx`)
3. 编写测试用例
4. 实现功能代码
5. 运行测试确保通过
6. 提交更改 (`git commit -m 'feat: xxx'`)
7. 推送到分支 (`git push origin feature/xxx`)
8. 创建Pull Request

---

## 许可证

MIT License

---

## 联系方式

- **GitHub**: https://github.com/minionszyw/cn5-lite
- **Issues**: https://github.com/minionszyw/cn5-lite/issues

---

**⚠️ 免责声明**: 本系统仅供学习和研究使用，不构成投资建议。量化交易存在风险，请谨慎使用。

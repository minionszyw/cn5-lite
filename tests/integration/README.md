# 集成测试文档

## 📋 概述

集成测试用于验证系统各模块之间的协作是否正常，以及完整业务流程是否符合预期。

## 🗂️ 测试文件

### 1. test_multi_datasource_integration.py

**测试内容**:
- 真实数据源API调用（AkShare/Baostock/Efinance）
- 数据缓存性能
- 数据源降级机制
- 数据质量验证
- 限流器功能
- 错误恢复

**运行方式**:
```bash
# 运行所有慢速测试（需要真实API）
pytest tests/integration/test_multi_datasource_integration.py -m slow -v

# 跳过慢速测试
pytest tests/integration/test_multi_datasource_integration.py -m "not slow" -v
```

**注意事项**:
- ⚠️ 需要网络连接
- ⚠️ 可能触发API限流
- ⚠️ 测试时间较长（30秒-2分钟）

---

### 2. test_api_endpoints.py

**测试内容**:
- 全部27个API端点的功能测试
- 请求/响应格式验证
- 错误处理
- 端到端流程

**测试覆盖**:
- ✅ 策略管理API（6个端点）
- ✅ 回测API（2个端点）
- ✅ 交易管理API（6个端点）
- ✅ 影子账户API（6个端点）
- ✅ 风控API（7个端点）

**运行方式**:
```bash
# 运行所有API测试
pytest tests/integration/test_api_endpoints.py -v

# 运行特定测试类
pytest tests/integration/test_api_endpoints.py::TestStrategyAPI -v
```

**注意事项**:
- ⚠️ 需要API服务运行（http://localhost:8000）
- ⚠️ 部分测试需要数据库
- ⚠️ 测试会创建和删除临时数据

---

### 3. test_strategy_lifecycle.py

**测试内容**:
- 策略完整生命周期：生成 → 回测 → 影子账户 → 晋升 → 自动交易
- 策略适配器一致性
- A股规则完整性
- 影子账户晋升流程
- 错误场景处理

**核心测试**:
1. **test_complete_strategy_lifecycle** - 完整生命周期测试
   - AI生成策略
   - 代码安全验证
   - 回测执行
   - 影子账户创建
   - 评分晋升
   - 自动交易初始化

2. **test_strategy_adapter_consistency** - T+1机制验证
3. **test_backtest_china_rules** - A股规则验证
4. **test_shadow_promotion_criteria** - 晋升条件判断

**运行方式**:
```bash
# 运行完整生命周期测试
pytest tests/integration/test_strategy_lifecycle.py::TestStrategyLifecycle::test_complete_strategy_lifecycle -v

# 运行所有生命周期测试
pytest tests/integration/test_strategy_lifecycle.py -v
```

**注意事项**:
- ⚠️ 需要配置OPENAI_API_KEY（AI生成部分）
- ⚠️ 测试时间较长（1-3分钟）
- ⚠️ 使用模拟数据（不依赖真实市场数据）

---

### 4. test_risk_control.py

**测试内容**:
- 7层风控完整验证
- 涨跌停检测
- 多策略资金分配
- 风险评分计算
- 风控与交易集成
- 黑名单管理
- 风控配置动态更新
- 紧急停止机制
- 风控日志和统计

**7层风控测试**:
1. 总资金止损（10%）
2. 黑名单股票
3. 单日亏损限制（5%）
4. 单策略资金占用（30%）
5. 单笔交易限制（20%）
6. 异常交易频率（20笔/小时）
7. 涨跌停板检测

**运行方式**:
```bash
# 运行所有风控测试
pytest tests/integration/test_risk_control.py -v

# 运行7层风控测试
pytest tests/integration/test_risk_control.py::TestRiskControlIntegration::test_seven_layer_risk_validation -v
```

**注意事项**:
- ✅ 不依赖外部服务
- ✅ 测试速度快（秒级）
- ✅ 使用模拟数据

---

## 🚀 运行所有集成测试

### 快速测试（跳过慢速）

```bash
pytest tests/integration/ -m "not slow" -v
```

### 完整测试（包含慢速）

```bash
pytest tests/integration/ -m slow -v
```

### 带覆盖率的测试

```bash
pytest tests/integration/ --cov=app --cov-report=html -v
```

### 并行测试（加速）

```bash
pytest tests/integration/ -n auto -v
```

## 📊 测试统计

| 测试文件 | 测试类数 | 测试用例数 | 预计时间 |
|---------|---------|-----------|----------|
| test_multi_datasource_integration.py | 5 | 12 | 30-120秒 |
| test_api_endpoints.py | 6 | 27 | 10-30秒 |
| test_strategy_lifecycle.py | 3 | 8 | 60-180秒 |
| test_risk_control.py | 4 | 12 | 5-15秒 |
| **总计** | **18** | **59** | **2-5分钟** |

## 🔧 配置要求

### 环境变量

```bash
# .env文件
OPENAI_API_KEY=sk-xxx  # AI生成测试需要
API_BASE_URL=http://localhost:8000/api/v1  # API端点测试需要
```

### 依赖服务

集成测试可能需要以下服务运行：

- ✅ FastAPI服务（http://localhost:8000）
- ✅ SQLite数据库（自动创建）
- ⚠️ Redis（可选，缓存测试需要）
- ⚠️ 网络连接（数据源测试需要）

## 📝 pytest标记说明

### @pytest.mark.integration

标记为集成测试，测试多个模块协作

```python
@pytest.mark.integration
def test_complete_flow():
    # 测试完整业务流程
    pass
```

### @pytest.mark.slow

标记为慢速测试，通常需要真实API调用或长时间计算

```python
@pytest.mark.slow
@pytest.mark.integration
def test_real_api_call():
    # 调用真实API
    pass
```

### 筛选运行

```bash
# 只运行快速测试
pytest -m "not slow"

# 只运行慢速测试
pytest -m slow

# 只运行集成测试
pytest -m integration
```

## 🐛 常见问题

### Q: test_multi_datasource_integration.py 测试失败？

**可能原因**:
- 网络连接问题
- API限流（AkShare限制1次/秒）
- 股票代码不存在

**解决方法**:
```bash
# 跳过真实API测试
pytest -m "not slow"

# 或设置更长的超时
pytest --timeout=300
```

### Q: test_api_endpoints.py 测试失败？

**可能原因**:
- API服务未启动
- 数据库未初始化
- 端口被占用

**解决方法**:
```bash
# 启动API服务
uvicorn app.api.main:app --reload

# 初始化数据库
python -c "from app.database import init_db; init_db()"
```

### Q: test_strategy_lifecycle.py AI生成失败？

**可能原因**:
- OPENAI_API_KEY未配置
- API额度用尽
- 网络问题

**解决方法**:
```bash
# 配置环境变量
export OPENAI_API_KEY=sk-xxx

# 或跳过AI生成测试
pytest --deselect tests/integration/test_strategy_lifecycle.py::TestStrategyLifecycle::test_complete_strategy_lifecycle
```

## 📈 持续集成（CI）

### GitHub Actions 示例

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run fast integration tests
        run: |
          pytest tests/integration/ -m "not slow" -v

      - name: Run slow integration tests
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        run: |
          pytest tests/integration/ -m slow -v
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## 🎯 最佳实践

1. **本地开发**: 只运行快速测试
   ```bash
   pytest tests/integration/ -m "not slow" -v
   ```

2. **PR提交前**: 运行完整测试
   ```bash
   pytest tests/integration/ -v
   ```

3. **定期回归**: 每周运行慢速测试验证外部API
   ```bash
   pytest tests/integration/ -m slow -v
   ```

4. **发布前**: 运行所有测试+覆盖率
   ```bash
   pytest tests/integration/ --cov=app --cov-report=html -v
   ```

## 📚 参考资料

- **pytest文档**: https://docs.pytest.org
- **FastAPI测试**: https://fastapi.tiangolo.com/tutorial/testing/
- **pytest-cov**: https://pytest-cov.readthedocs.io

---

**最后更新**: 2025-11-30
**测试覆盖率目标**: >80%

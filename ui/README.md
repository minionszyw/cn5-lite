# CN5-Lite Streamlit前端界面

## 📋 目录结构

```
ui/
├── app.py                  # 主页（系统概览）
├── pages/                  # 多页面应用
│   ├── 1_策略生成.py       # AI策略生成页面
│   ├── 2_回测分析.py       # 回测分析页面
│   ├── 3_影子账户.py       # 影子账户管理页面
│   ├── 4_交易管理.py       # 交易管理页面
│   └── 5_风控配置.py       # 风控配置页面
└── README.md              # 本文件
```

## 🚀 快速启动

### 方式1: 使用启动脚本（推荐）

```bash
# 在项目根目录执行
./start_ui.sh
```

### 方式2: 手动启动

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动Streamlit
streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
```

### 方式3: Docker启动（未来支持）

```bash
docker-compose up ui
```

## 🌐 访问地址

启动后访问: **http://localhost:8501**

## 📚 页面功能

### 🏠 主页（app.py）

**功能**:
- 系统概览和统计
- 快速导航
- 健康检查

**特性**:
- 实时数据统计（策略数、运行数、收益等）
- 快速入口按钮
- 系统特性展示
- API连接状态检查

---

### 🧠 策略生成（1_策略生成.py）

**功能**:
- AI生成策略代码
- 策略代码验证
- 策略保存和管理

**特性**:
- 预设示例策略
- 自然语言输入
- 高级选项（止损、目标股票等）
- 安全检查结果展示
- 已保存策略列表

**使用流程**:
1. 选择示例或输入自定义策略描述
2. 配置高级选项（可选）
3. 点击"生成策略"
4. 查看代码和安全检查结果
5. 保存策略或立即回测

---

### 📊 回测分析（2_回测分析.py）

**功能**:
- 运行策略回测
- 查看性能指标
- 资金曲线可视化
- 交易记录查看

**特性**:
- 灵活的日期范围选择
- A股规则开关
- 完整的性能指标展示
- 资金曲线图（Plotly）
- 交易记录下载
- 历史回测记录

**性能指标**:
- 年化收益率
- 夏普比率
- 最大回撤
- 胜率
- 总交易次数
- 波动率

---

### 👥 影子账户（3_影子账户.py）

**功能**:
- 创建影子账户
- 查看排行榜
- 管理我的账户
- 晋升到实盘

**特性**:
- Top 10排行榜可视化
- 5维度综合评分
- 时间衰减权重
- 自动晋升判断
- 详细性能指标

**评分维度**:
1. 年化收益率（30%）
2. 夏普比率（25%）
3. 最大回撤（20%）
4. 波动率（15%）
5. 胜率（10%）

**晋升条件**:
- 综合得分 ≥ 35分
- 观察天数 ≥ 14天

---

### 💹 交易管理（4_交易管理.py）

**功能**:
- 启动/停止自动交易
- 查看交易记录
- 配置交易参数
- 状态恢复

**特性**:
- 实时交易状态监控
- 运行中策略展示
- 交易模式选择（免确认/需确认）
- 交易记录筛选和下载
- 断点续传（容器重启恢复）

**交易模式**:
- **免确认模式**: 单笔≤3000元自动执行
- **需确认模式**: 所有交易需手动审核

---

### 🛡️ 风控配置（5_风控配置.py）

**功能**:
- 配置7层风控参数
- 管理黑名单股票
- 查看风控日志

**特性**:
- 表单化配置界面
- 实时参数预览
- 黑名单批量管理
- 风控拦截日志
- 风险评分统计

**7层风控**:
1. 总资金止损（10%）
2. 黑名单股票
3. 单日亏损限制（5%）
4. 单策略资金占用（30%）
5. 单笔交易限制（20%）
6. 异常交易频率（20次/小时）
7. 涨跌停板检测

---

## ⚙️ 配置说明

### 环境变量

UI通过环境变量与API通信：

```bash
# .env文件
API_BASE_URL=http://localhost:8000/api/v1  # API基础URL
```

### Streamlit配置

可选：创建 `.streamlit/config.toml` 自定义配置：

```toml
[server]
port = 8501
address = "0.0.0.0"

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

## 📊 数据流

```
UI (Streamlit) → API (FastAPI) → Services → Database
     ↓               ↓              ↓
  用户交互        RESTful        业务逻辑
```

**通信方式**:
- UI通过 `requests` 库调用API端点
- API返回JSON格式数据
- UI使用Streamlit组件展示

## 🎨 UI组件

### 使用的Streamlit组件

- `st.metric()` - 指标展示
- `st.plotly_chart()` - Plotly图表
- `st.dataframe()` - 数据表格
- `st.expander()` - 可折叠区域
- `st.tabs()` - 标签页
- `st.form()` - 表单
- `st.button()` - 按钮
- `st.selectbox()` - 下拉选择
- `st.slider()` - 滑块
- `st.text_input()` - 文本输入

### 图表库

- **Plotly**: 交互式图表（资金曲线、排行榜等）
- **Pandas**: 数据表格展示

## 🔧 开发说明

### 添加新页面

1. 在 `ui/pages/` 创建新文件（如 `6_新功能.py`）
2. 文件名格式：`序号_页面名.py`
3. 在主页 `app.py` 的侧边栏添加导航链接

```python
# ui/pages/6_新功能.py
import streamlit as st

st.set_page_config(page_title="新功能", page_icon="🎯", layout="wide")
st.title("🎯 新功能")
# 页面内容...
```

### API调用模式

```python
import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

try:
    response = requests.get(f"{API_BASE_URL}/endpoint", timeout=30)

    if response.status_code == 200:
        data = response.json().get("data", {})
        # 处理数据...
    else:
        st.error(f"请求失败: {response.status_code}")

except requests.exceptions.RequestException as e:
    st.error(f"请求错误: {e}")
```

### 缓存优化

使用 `@st.cache_data` 缓存API数据：

```python
@st.cache_data(ttl=60)  # 缓存60秒
def get_strategies():
    response = requests.get(f"{API_BASE_URL}/strategies")
    return response.json().get("data", [])
```

## 🐛 调试

### 启用调试模式

```bash
streamlit run ui/app.py --logger.level debug
```

### 查看日志

Streamlit日志输出到控制台，包括：
- 页面加载信息
- 组件渲染信息
- 错误堆栈

## 📦 依赖

主要依赖（已在 requirements.txt）：

- `streamlit==1.30.0` - Web框架
- `plotly==5.18.0` - 交互式图表
- `pandas==2.1.4` - 数据处理
- `requests` - HTTP客户端

## ⚠️ 注意事项

1. **API服务**: UI依赖API服务，确保API已启动（http://localhost:8000）
2. **环境变量**: 配置正确的 `API_BASE_URL`
3. **会话状态**: Streamlit使用 `st.session_state` 管理状态，页面刷新会重置
4. **并发限制**: Streamlit默认单线程，大量并发请求可能影响性能

## 📖 参考文档

- **Streamlit官方文档**: https://docs.streamlit.io
- **Plotly文档**: https://plotly.com/python/
- **API文档**: http://localhost:8000/docs

## 🤝 贡献

欢迎改进UI设计和交互体验！

---

**最后更新**: 2025-11-30
**版本**: 1.0.0

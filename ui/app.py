"""
CN5-Lite Streamlit前端主页
"""
import streamlit as st
import requests
from datetime import datetime
import os

# 页面配置
st.set_page_config(
    page_title="CN5-Lite AI量化交易系统",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API基础URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

# 侧边栏
with st.sidebar:
    st.title("🤖 CN5-Lite")
    st.markdown("---")
    st.markdown("### 导航")

    # 导航链接
    st.page_link("app.py", label="🏠 主页", icon="🏠")
    st.page_link("pages/1_策略生成.py", label="🧠 策略生成", icon="🧠")
    st.page_link("pages/2_回测分析.py", label="📊 回测分析", icon="📊")
    st.page_link("pages/3_影子账户.py", label="👥 影子账户", icon="👥")
    st.page_link("pages/4_交易管理.py", label="💹 交易管理", icon="💹")
    st.page_link("pages/5_风控配置.py", label="🛡️ 风控配置", icon="🛡️")

    st.markdown("---")
    st.markdown("### 系统信息")
    st.info(f"**版本**: 1.0.0\n**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 主页面
st.title("🏠 CN5-Lite AI量化交易系统")
st.markdown("### 轻量级AI驱动的A股量化交易系统")

# 系统状态概览
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📝 策略总数",
        value="--",
        delta="加载中...",
        help="系统中的策略总数"
    )

with col2:
    st.metric(
        label="✅ 运行中策略",
        value="--",
        delta="加载中...",
        help="正在运行的策略数量"
    )

with col3:
    st.metric(
        label="👥 影子账户",
        value="--",
        delta="加载中...",
        help="观察中的影子账户数量"
    )

with col4:
    st.metric(
        label="💰 今日收益",
        value="--",
        delta="加载中...",
        help="今日总收益"
    )

st.markdown("---")

# 快速开始
st.markdown("## 🚀 快速开始")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 1️⃣ AI生成策略")
    st.markdown("""
    使用自然语言描述您的交易想法，AI将自动生成可执行的策略代码。

    **示例**:
    - "双均线策略，MA5/MA20金叉买入"
    - "布林带突破策略"
    - "MACD金叉+RSI超卖组合"
    """)
    if st.button("🧠 开始生成策略", use_container_width=True):
        st.switch_page("pages/1_策略生成.py")

with col2:
    st.markdown("### 2️⃣ 回测验证")
    st.markdown("""
    在历史数据上验证策略表现，完整模拟A股市场规则。

    **特性**:
    - ✅ T+1制度
    - ✅ 涨跌停限制
    - ✅ 真实税费计算
    - ✅ 停牌检测
    """)
    if st.button("📊 运行回测", use_container_width=True):
        st.switch_page("pages/2_回测分析.py")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 3️⃣ 影子账户筛选")
    st.markdown("""
    策略在观察模式下运行，系统自动评分排名，优质策略自动晋升。

    **评分维度**:
    - 年化收益率（30%）
    - 夏普比率（25%）
    - 最大回撤（20%）
    - 波动率（15%）
    - 胜率（10%）
    """)
    if st.button("👥 查看影子账户", use_container_width=True):
        st.switch_page("pages/3_影子账户.py")

with col2:
    st.markdown("### 4️⃣ 自动交易")
    st.markdown("""
    启动AI自动交易，支持免确认和需确认两种模式。

    **安全保障**:
    - 🛡️ 7层风控验证
    - 💰 单笔金额限制
    - 🚫 黑名单机制
    - 📊 实时监控
    """)
    if st.button("💹 交易管理", use_container_width=True):
        st.switch_page("pages/4_交易管理.py")

st.markdown("---")

# 系统特性
st.markdown("## ✨ 核心特性")

feature_col1, feature_col2, feature_col3 = st.columns(3)

with feature_col1:
    st.markdown("""
    ### 🧠 AI策略研究员
    - 自然语言生成策略
    - 代码安全检查
    - 沙箱执行验证
    - 自动逻辑测试
    """)

with feature_col2:
    st.markdown("""
    ### 📊 完整A股适配
    - T+1制度
    - 涨跌停限制（±10%/±5%/±20%）
    - 印花税+佣金
    - 停牌检测
    """)

with feature_col3:
    st.markdown("""
    ### 🛡️ 多层风控
    - 总资金止损（10%）
    - 单日亏损限制（5%）
    - 单策略资金限制（30%）
    - 交易频率控制
    """)

st.markdown("---")

# 使用指南
with st.expander("📖 使用指南"):
    st.markdown("""
    ### 推荐流程

    1. **策略生成** → 使用AI生成策略或手动编写策略代码
    2. **回测验证** → 在历史数据上验证策略表现
    3. **影子账户** → 策略在观察模式下运行7-14天
    4. **评分晋升** → 得分≥35分且观察≥14天自动晋升
    5. **自动交易** → 启动AI自动交易（模拟盘）

    ### 风险提示

    ⚠️ **本系统仅供学习和研究使用，不构成投资建议**

    - 量化交易存在风险，历史收益不代表未来表现
    - 建议从小资金开始，充分测试后再增加投入
    - 密切关注市场变化，及时调整策略参数
    """)

# API连接状态检查
with st.expander("🔧 系统健康检查"):
    if st.button("检查API连接"):
        try:
            response = requests.get(f"{API_BASE_URL.replace('/api/v1', '')}/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ API服务正常运行")
                st.json(response.json())
            else:
                st.error(f"❌ API响应异常: {response.status_code}")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ 无法连接到API服务: {e}")
            st.warning(f"请确保API服务运行在: {API_BASE_URL}")

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>CN5-Lite v1.0.0 | MIT License |
    <a href='https://github.com/minionszyw/cn5-lite' target='_blank'>GitHub</a>
    </p>
</div>
""", unsafe_allow_html=True)

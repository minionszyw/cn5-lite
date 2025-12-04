"""
影子账户页面
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os

st.set_page_config(page_title="影子账户", page_icon="👥", layout="wide")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.title("👥 影子账户管理")
st.markdown("策略在观察模式下运行，系统自动评分排名，优质策略自动晋升")

# 获取策略列表
@st.cache_data(ttl=60)
def get_strategies():
    try:
        response = requests.get(f"{API_BASE_URL}/strategies")
        if response.status_code == 200:
            return response.json().get("data", [])
    except:
        return []
    return []

# Tab布局
tab1, tab2, tab3 = st.tabs(["📊 排行榜", "➕ 创建账户", "📋 我的账户"])

with tab1:
    st.markdown("### 🏆 影子账户排行榜")

    # 获取Top排名
    try:
        top_response = requests.get(f"{API_BASE_URL}/shadow/top", params={"limit": 10})

        if top_response.status_code == 200:
            top_accounts = top_response.json().get("data", [])

            if top_accounts:
                # 使用柱状图展示Top 10
                df_top = pd.DataFrame(top_accounts)

                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=df_top["ranking"],
                    y=df_top["weighted_score"],
                    text=df_top["strategy_name"],
                    textposition='auto',
                    marker=dict(
                        color=df_top["weighted_score"],
                        colorscale='Viridis',
                        showscale=True
                    )
                ))

                fig.update_layout(
                    title="影子账户评分排名",
                    xaxis_title="排名",
                    yaxis_title="综合评分",
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)

                # 详细列表
                st.markdown("#### 详细信息")

                for idx, account in enumerate(top_accounts, 1):
                    with st.expander(
                        f"{'🥇' if idx == 1 else '🥈' if idx == 2 else '🥉' if idx == 3 else '📊'} "
                        f"#{account.get('ranking')} {account.get('strategy_name', 'N/A')} "
                        f"(得分: {account.get('weighted_score', 0):.2f})"
                    ):
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("综合得分", f"{account.get('weighted_score', 0):.2f}")
                            st.metric("观察天数", f"{account.get('observation_days', 0)}天")

                        with col2:
                            st.metric("年化收益", f"{account.get('annual_return', 0):.2%}")
                            st.metric("夏普比率", f"{account.get('sharpe_ratio', 0):.2f}")

                        with col3:
                            st.metric("最大回撤", f"{account.get('max_drawdown', 0):.2%}")
                            st.metric("波动率", f"{account.get('volatility', 0):.2%}")

                        with col4:
                            st.metric("胜率", f"{account.get('win_rate', 0):.2%}")
                            st.metric("状态", account.get("status", "N/A"))

                        # 晋升按钮
                        if account.get("can_promote", False):
                            if st.button(f"🚀 晋升到实盘", key=f"promote_{account['id']}"):
                                promote_response = requests.post(
                                    f"{API_BASE_URL}/shadow/accounts/{account['id']}/promote"
                                )

                                if promote_response.status_code == 200:
                                    st.success("✅ 已晋升到实盘！")
                                    st.rerun()
                                else:
                                    st.error(f"晋升失败: {promote_response.text}")
                        else:
                            st.info("⏳ 未达到晋升条件（得分≥35，观察≥14天）")

            else:
                st.info("暂无影子账户")
        else:
            st.error("无法获取排行榜数据")

    except requests.exceptions.RequestException as e:
        st.error(f"请求失败: {e}")

with tab2:
    st.markdown("### ➕ 创建影子账户")

    st.info("💡 影子账户在观察模式下运行，不进行真实交易，用于评估策略表现")

    strategies = get_strategies()

    if strategies:
        # 选择策略
        strategy_options = {f"{s['name']} (ID: {s['id']})": s['id'] for s in strategies}
        selected_strategy_name = st.selectbox(
            "选择策略",
            options=list(strategy_options.keys())
        )
        selected_strategy_id = strategy_options[selected_strategy_name]

        # 配置参数
        col1, col2 = st.columns(2)

        with col1:
            initial_cash = st.number_input(
                "初始资金（元）",
                min_value=10000,
                max_value=1000000,
                value=100000,
                step=10000
            )

        with col2:
            observation_days = st.number_input(
                "观察天数",
                min_value=1,
                max_value=90,
                value=7,
                help="策略在影子模式下运行的天数"
            )

        # 评分权重说明
        with st.expander("📊 评分维度说明"):
            st.markdown("""
            系统使用5个维度对策略进行综合评分：

            1. **年化收益率** (权重30%) - 策略的年化投资回报
            2. **夏普比率** (权重25%) - 风险调整后收益
            3. **最大回撤** (权重20%) - 从峰值到谷底的最大跌幅
            4. **波动率** (权重15%) - 收益的稳定性
            5. **胜率** (权重10%) - 盈利交易占比

            **晋升条件**:
            - 综合得分 ≥ 35分
            - 观察天数 ≥ 14天

            **时间衰减**: 使用指数衰减，半衰期7天，越近期的表现权重越高
            """)

        # 创建按钮
        if st.button("🚀 创建影子账户", type="primary", use_container_width=True):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/shadow/accounts",
                    json={
                        "strategy_id": selected_strategy_id,
                        "initial_cash": initial_cash,
                        "observation_days": observation_days
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ 影子账户创建成功！账户ID: {result.get('id')}")
                    st.info("账户已开始观察运行，可在'我的账户'标签查看进度")
                    st.rerun()
                else:
                    st.error(f"创建失败: {response.text}")

            except requests.exceptions.RequestException as e:
                st.error(f"请求失败: {e}")

    else:
        st.warning("暂无可用策略，请先生成策略")

with tab3:
    st.markdown("### 📋 我的影子账户")

    try:
        accounts_response = requests.get(f"{API_BASE_URL}/shadow/accounts")

        if accounts_response.status_code == 200:
            accounts = accounts_response.json().get("data", [])

            if accounts:
                for account in accounts:
                    status_color = {
                        "running": "🟢",
                        "promoted": "🚀",
                        "terminated": "🔴"
                    }.get(account.get("status"), "⚪")

                    with st.expander(
                        f"{status_color} 账户ID: {account['id']} | "
                        f"策略: {account.get('strategy_name', 'N/A')} | "
                        f"得分: {account.get('weighted_score', 0):.2f}"
                    ):
                        # 基本信息
                        info_col1, info_col2, info_col3 = st.columns(3)

                        with info_col1:
                            st.metric("状态", account.get("status", "N/A"))
                            st.metric("初始资金", f"¥{account.get('initial_cash', 0):,.0f}")

                        with info_col2:
                            st.metric("观察天数", f"{account.get('observation_days', 0)}天")
                            st.metric("已运行天数", f"{account.get('elapsed_days', 0)}天")

                        with info_col3:
                            st.metric("综合得分", f"{account.get('weighted_score', 0):.2f}")
                            st.metric("排名", f"#{account.get('ranking', '--')}")

                        st.markdown("---")

                        # 详细性能
                        perf_col1, perf_col2, perf_col3, perf_col4, perf_col5 = st.columns(5)

                        with perf_col1:
                            st.metric("年化收益", f"{account.get('annual_return', 0):.2%}")

                        with perf_col2:
                            st.metric("夏普比率", f"{account.get('sharpe_ratio', 0):.2f}")

                        with perf_col3:
                            st.metric("最大回撤", f"{account.get('max_drawdown', 0):.2%}")

                        with perf_col4:
                            st.metric("波动率", f"{account.get('volatility', 0):.2%}")

                        with perf_col5:
                            st.metric("胜率", f"{account.get('win_rate', 0):.2%}")

                        # 操作按钮
                        st.markdown("---")
                        btn_col1, btn_col2, btn_col3 = st.columns(3)

                        with btn_col1:
                            # 查看详情
                            if st.button("📊 查看详情", key=f"detail_{account['id']}"):
                                detail_response = requests.get(
                                    f"{API_BASE_URL}/shadow/accounts/{account['id']}"
                                )

                                if detail_response.status_code == 200:
                                    detail = detail_response.json()
                                    st.json(detail)

                        with btn_col2:
                            # 终止账户
                            if account.get("status") == "running":
                                if st.button("⏹️ 终止", key=f"terminate_{account['id']}"):
                                    terminate_response = requests.post(
                                        f"{API_BASE_URL}/shadow/accounts/{account['id']}/terminate"
                                    )

                                    if terminate_response.status_code == 200:
                                        st.success("✅ 已终止")
                                        st.rerun()
                                    else:
                                        st.error("终止失败")

                        with btn_col3:
                            # 晋升
                            if account.get("can_promote"):
                                if st.button("🚀 晋升", key=f"promote_my_{account['id']}"):
                                    promote_response = requests.post(
                                        f"{API_BASE_URL}/shadow/accounts/{account['id']}/promote"
                                    )

                                    if promote_response.status_code == 200:
                                        st.success("✅ 已晋升")
                                        st.rerun()
                                    else:
                                        st.error("晋升失败")
            else:
                st.info("暂无影子账户，请创建")
        else:
            st.error("无法获取账户列表")

    except requests.exceptions.RequestException as e:
        st.error(f"请求失败: {e}")

# 使用说明
with st.expander("💡 使用说明"):
    st.markdown("""
    ### 什么是影子账户？

    影子账户是策略在**观察模式**下运行的虚拟账户：
    - ✅ 使用真实市场数据
    - ✅ 执行策略逻辑
    - ✅ 记录交易信号
    - ❌ 不进行真实交易
    - ❌ 不占用真实资金

    ### 工作流程

    1. **创建账户** → 选择策略，设置初始资金和观察天数
    2. **观察运行** → 系统每日自动运行策略，记录表现
    3. **自动评分** → 根据5个维度计算综合得分
    4. **排名晋升** → 达到条件（得分≥35，观察≥14天）可晋升实盘

    ### 评分机制

    **5维度加权评分**:
    - 年化收益率（30%）
    - 夏普比率（25%）
    - 最大回撤（20%）
    - 波动率（15%）
    - 胜率（10%）

    **时间衰减**: 越近期的表现权重越高（半衰期7天）

    ### 注意事项

    - ⚠️ 影子账户表现不代表实盘表现
    - ⚠️ 建议观察至少14天再决定是否晋升
    - ⚠️ 市场环境变化可能影响策略表现
    """)

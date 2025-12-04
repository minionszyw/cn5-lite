"""
交易管理页面
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="交易管理", page_icon="💹", layout="wide")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.title("💹 交易管理")
st.markdown("启动AI自动交易，支持免确认和需确认两种模式")

# 获取策略列表
@st.cache_data(ttl=60)
def get_strategies():
    try:
        response = requests.get(f"{API_BASE_URL}/strategies", params={"status": "live"})
        if response.status_code == 200:
            return response.json().get("data", [])
    except:
        return []
    return []

# Tab布局
tab1, tab2, tab3 = st.tabs(["🎮 交易控制", "📊 交易记录", "⚙️ 配置"])

with tab1:
    st.markdown("### 🎮 交易控制台")

    # 获取交易状态
    try:
        status_response = requests.get(f"{API_BASE_URL}/trading/status")

        if status_response.status_code == 200:
            trading_status = status_response.json().get("data", {})

            # 状态概览
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                is_running = trading_status.get("is_running", False)
                status_text = "🟢 运行中" if is_running else "🔴 已停止"
                st.metric("交易状态", status_text)

            with col2:
                active_strategies = trading_status.get("active_strategies", 0)
                st.metric("活跃策略", active_strategies)

            with col3:
                today_trades = trading_status.get("today_trades", 0)
                st.metric("今日交易", today_trades)

            with col4:
                today_pnl = trading_status.get("today_pnl", 0)
                st.metric(
                    "今日盈亏",
                    f"¥{today_pnl:,.2f}",
                    delta=f"{today_pnl:,.2f}",
                    delta_color="normal"
                )

            st.markdown("---")

            # 运行中的策略
            if is_running and trading_status.get("running_strategies"):
                st.markdown("#### 🏃 运行中的策略")

                for strategy in trading_status["running_strategies"]:
                    with st.expander(f"📝 {strategy.get('name')} (ID: {strategy.get('id')})"):
                        strat_col1, strat_col2, strat_col3 = st.columns(3)

                        with strat_col1:
                            st.metric("持仓数", strategy.get("positions_count", 0))
                            st.metric("持仓市值", f"¥{strategy.get('positions_value', 0):,.2f}")

                        with strat_col2:
                            st.metric("今日交易", strategy.get("today_trades", 0))
                            st.metric("今日盈亏", f"¥{strategy.get('today_pnl', 0):,.2f}")

                        with strat_col3:
                            st.metric("累计盈亏", f"¥{strategy.get('total_pnl', 0):,.2f}")
                            st.metric("胜率", f"{strategy.get('win_rate', 0):.2%}")

                        # 停止单个策略
                        if st.button(f"⏹️ 停止此策略", key=f"stop_strategy_{strategy['id']}"):
                            stop_response = requests.post(
                                f"{API_BASE_URL}/trading/stop",
                                json={"strategy_id": strategy['id']}
                            )

                            if stop_response.status_code == 200:
                                st.success("✅ 策略已停止")
                                st.rerun()
                            else:
                                st.error("停止失败")

        else:
            trading_status = {"is_running": False}
            st.warning("无法获取交易状态")

    except requests.exceptions.RequestException as e:
        trading_status = {"is_running": False}
        st.error(f"请求失败: {e}")

    st.markdown("---")

    # 启动/停止交易
    col_ctrl1, col_ctrl2 = st.columns(2)

    with col_ctrl1:
        st.markdown("#### 🚀 启动交易")

        strategies = get_strategies()

        if strategies:
            # 选择策略
            strategy_options = {f"{s['name']} (ID: {s['id']})": s['id'] for s in strategies}
            selected_strategy_name = st.selectbox(
                "选择策略",
                options=list(strategy_options.keys()),
                key="start_strategy_select"
            )
            selected_strategy_id = strategy_options[selected_strategy_name]

            # 交易模式
            trading_mode = st.radio(
                "交易模式",
                ["免确认模式", "需确认模式"],
                help="免确认: ≤3000元自动执行 | 需确认: 所有交易需审核"
            )

            require_approval = (trading_mode == "需确认模式")

            # 启动按钮
            if st.button("🚀 启动自动交易", type="primary", use_container_width=True):
                try:
                    start_response = requests.post(
                        f"{API_BASE_URL}/trading/start",
                        json={
                            "strategy_id": selected_strategy_id,
                            "require_approval": require_approval
                        }
                    )

                    if start_response.status_code == 200:
                        st.success("✅ 自动交易已启动！")
                        st.rerun()
                    else:
                        st.error(f"启动失败: {start_response.text}")

                except requests.exceptions.RequestException as e:
                    st.error(f"请求失败: {e}")
        else:
            st.info("暂无可交易策略，请先将策略晋升到实盘")

    with col_ctrl2:
        st.markdown("#### ⏹️ 停止交易")

        st.warning("停止交易将关闭所有持仓并停止策略运行")

        # 停止选项
        close_positions = st.checkbox("同时平仓所有持仓", value=True)

        # 停止按钮
        if st.button("⏹️ 停止所有交易", type="secondary", use_container_width=True):
            try:
                stop_response = requests.post(
                    f"{API_BASE_URL}/trading/stop",
                    json={"close_positions": close_positions}
                )

                if stop_response.status_code == 200:
                    st.success("✅ 交易已停止")
                    st.rerun()
                else:
                    st.error(f"停止失败: {stop_response.text}")

            except requests.exceptions.RequestException as e:
                st.error(f"请求失败: {e}")

with tab2:
    st.markdown("### 📊 交易记录")

    # 筛选选项
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        date_range = st.selectbox(
            "时间范围",
            ["今天", "最近7天", "最近30天", "自定义"],
            key="trade_date_range"
        )

    with filter_col2:
        action_filter = st.selectbox(
            "交易方向",
            ["全部", "买入", "卖出"],
            key="trade_action_filter"
        )

    with filter_col3:
        strategy_filter = st.selectbox(
            "策略筛选",
            ["全部策略"] + [s['name'] for s in get_strategies()],
            key="trade_strategy_filter"
        )

    # 获取交易记录
    try:
        # 构建查询参数
        params = {"limit": 100}

        if date_range == "今天":
            params["start_date"] = datetime.now().strftime("%Y-%m-%d")
        elif date_range == "最近7天":
            params["start_date"] = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        elif date_range == "最近30天":
            params["start_date"] = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        if action_filter != "全部":
            params["action"] = action_filter.lower()

        trades_response = requests.get(f"{API_BASE_URL}/trading/trades", params=params)

        if trades_response.status_code == 200:
            trades = trades_response.json().get("data", [])

            if trades:
                # 转换为DataFrame
                df_trades = pd.DataFrame(trades)

                # 统计信息
                stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

                with stat_col1:
                    st.metric("总交易", len(df_trades))

                with stat_col2:
                    buy_count = len(df_trades[df_trades["action"] == "buy"]) if "action" in df_trades.columns else 0
                    st.metric("买入次数", buy_count)

                with stat_col3:
                    sell_count = len(df_trades[df_trades["action"] == "sell"]) if "action" in df_trades.columns else 0
                    st.metric("卖出次数", sell_count)

                with stat_col4:
                    total_pnl = df_trades["pnl"].sum() if "pnl" in df_trades.columns else 0
                    st.metric(
                        "总盈亏",
                        f"¥{total_pnl:,.2f}",
                        delta=f"{total_pnl:,.2f}"
                    )

                st.markdown("---")

                # 交易列表
                st.dataframe(
                    df_trades[["trade_time", "symbol", "action", "price", "volume", "amount", "pnl"]].head(50),
                    use_container_width=True,
                    hide_index=True
                )

                # 下载
                csv = df_trades.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 下载交易记录",
                    data=csv,
                    file_name=f"trades_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

            else:
                st.info("暂无交易记录")
        else:
            st.error("无法获取交易记录")

    except requests.exceptions.RequestException as e:
        st.error(f"请求失败: {e}")

with tab3:
    st.markdown("### ⚙️ 交易配置")

    st.info("💡 这些配置影响AI自动交易的行为")

    config_col1, config_col2 = st.columns(2)

    with config_col1:
        st.markdown("#### 🔧 基础配置")

        require_approval = st.checkbox(
            "需要确认",
            value=False,
            help="所有交易需手动审核后执行"
        )

        auto_approve_threshold = st.number_input(
            "自动审批阈值（元）",
            min_value=0,
            max_value=100000,
            value=3000,
            step=100,
            help="小于此金额的交易自动执行（仅在免确认模式）",
            disabled=require_approval
        )

        max_capital_ratio = st.slider(
            "AI最大资金占比",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.05,
            format="%.0f%%",
            help="AI自动交易最多使用总资金的比例"
        )

    with config_col2:
        st.markdown("#### 🛡️ 安全配置")

        enable_logic_test = st.checkbox(
            "启用逻辑测试",
            value=True,
            help="启动前测试策略逻辑（空数据、极端行情等）"
        )

        enable_rehydrate = st.checkbox(
            "启用断点续传",
            value=True,
            help="容器重启时自动恢复策略状态"
        )

        max_retry = st.number_input(
            "最大重试次数",
            min_value=0,
            max_value=10,
            value=3,
            help="交易失败时的重试次数"
        )

    # 保存配置
    if st.button("💾 保存配置", type="primary", use_container_width=True):
        try:
            config_response = requests.put(
                f"{API_BASE_URL}/trading/config",
                json={
                    "require_approval": require_approval,
                    "auto_approve_threshold": auto_approve_threshold,
                    "max_capital_ratio": max_capital_ratio,
                    "enable_logic_test": enable_logic_test,
                    "enable_rehydrate": enable_rehydrate,
                    "max_retry": max_retry
                }
            )

            if config_response.status_code == 200:
                st.success("✅ 配置已保存")
            else:
                st.error(f"保存失败: {config_response.text}")

        except requests.exceptions.RequestException as e:
            st.error(f"请求失败: {e}")

    # 状态恢复
    st.markdown("---")
    st.markdown("#### 🔄 状态恢复")

    st.info("容器重启后，系统会自动恢复策略状态（持仓、指标、T+1锁定）")

    strategies_for_rehydrate = get_strategies()

    if strategies_for_rehydrate:
        rehydrate_strategy_options = {f"{s['name']} (ID: {s['id']})": s['id'] for s in strategies_for_rehydrate}
        selected_rehydrate_strategy_name = st.selectbox(
            "选择要恢复的策略",
            options=list(rehydrate_strategy_options.keys()),
            key="rehydrate_strategy_select"
        )
        selected_rehydrate_strategy_id = rehydrate_strategy_options[selected_rehydrate_strategy_name]

        if st.button("🔄 手动恢复状态", use_container_width=True):
            try:
                rehydrate_response = requests.post(
                    f"{API_BASE_URL}/trading/rehydrate/{selected_rehydrate_strategy_id}"
                )

                if rehydrate_response.status_code == 200:
                    result = rehydrate_response.json().get("data", {})
                    st.success("✅ 状态恢复成功")

                    st.json({
                        "恢复的持仓": result.get("positions", {}),
                        "指标已恢复": result.get("indicators_restored", False),
                        "T+1锁定": result.get("locked_positions", {})
                    })
                else:
                    st.error(f"恢复失败: {rehydrate_response.text}")

            except requests.exceptions.RequestException as e:
                st.error(f"请求失败: {e}")

# 使用说明
with st.expander("💡 使用说明"):
    st.markdown("""
    ### 交易模式说明

    **免确认模式**:
    - ✅ 单笔≤3000元自动执行
    - ✅ 适合小资金、高频策略
    - ⚠️ 需密切关注交易记录

    **需确认模式**:
    - ✅ 所有交易需手动审核
    - ✅ 更安全，适合大资金
    - ⚠️ 可能错过交易时机

    ### 断点续传机制

    当Docker容器重启时，系统会自动：
    1. 从trades表恢复持仓和成本价
    2. 重放历史K线恢复技术指标（MA等）
    3. 恢复T+1锁定持仓

    ### 安全提示

    - ⚠️ 首次使用建议小资金测试
    - ⚠️ 密切关注交易记录和盈亏
    - ⚠️ 定期检查风控配置
    - ⚠️ 市场异常时及时停止交易
    """)

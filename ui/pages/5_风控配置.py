"""
风控配置页面
"""
import streamlit as st
import requests
from datetime import datetime
import os

st.set_page_config(page_title="风控配置", page_icon="🛡️", layout="wide")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.title("🛡️ 风控配置")
st.markdown("7层风控防护，多维度风险控制")

# Tab布局
tab1, tab2, tab3 = st.tabs(["⚙️ 风控参数", "🚫 黑名单管理", "📊 风控日志"])

with tab1:
    st.markdown("### ⚙️ 7层风控参数配置")

    # 获取当前配置
    try:
        config_response = requests.get(f"{API_BASE_URL}/risk/config")

        if config_response.status_code == 200:
            current_config = config_response.json().get("data", {})
        else:
            current_config = {}
            st.warning("无法获取当前配置，使用默认值")

    except requests.exceptions.RequestException as e:
        current_config = {}
        st.error(f"请求失败: {e}")

    # 配置表单
    with st.form("risk_config_form"):
        st.markdown("#### 第1层：总资金止损")
        st.info("触发后停止所有交易，保护本金")

        total_capital = st.number_input(
            "总资金（元）",
            min_value=10000,
            max_value=100000000,
            value=current_config.get("total_capital", 100000),
            step=10000,
            help="账户总资金"
        )

        max_total_loss_rate = st.slider(
            "总资金止损比例",
            min_value=0.0,
            max_value=0.5,
            value=current_config.get("max_total_loss_rate", 0.10),
            step=0.01,
            format="%.0f%%",
            help="亏损达到此比例时停止所有交易（默认10%）"
        )

        st.markdown("---")
        st.markdown("#### 第2层：黑名单股票")
        st.info("禁止交易指定股票（ST、退市等）")
        st.caption("在'黑名单管理'标签页配置具体股票")

        st.markdown("---")
        st.markdown("#### 第3层：单日亏损限制")
        st.info("单日亏损达到限制后当天停止交易")

        max_daily_loss_rate = st.slider(
            "单日亏损限制比例",
            min_value=0.0,
            max_value=0.2,
            value=current_config.get("max_daily_loss_rate", 0.05),
            step=0.01,
            format="%.0f%%",
            help="单日亏损达到此比例时停止当天交易（默认5%）"
        )

        st.markdown("---")
        st.markdown("#### 第4层：单策略资金占用")
        st.info("限制单个策略使用的最大资金比例")

        max_strategy_capital_rate = st.slider(
            "单策略资金占用比例",
            min_value=0.0,
            max_value=1.0,
            value=current_config.get("max_strategy_capital_rate", 0.30),
            step=0.05,
            format="%.0f%%",
            help="单个策略最多使用总资金的比例（默认30%）"
        )

        st.markdown("---")
        st.markdown("#### 第5层：单笔交易限制")
        st.info("限制单笔交易金额占总资金比例")

        max_single_trade_rate = st.slider(
            "单笔交易限制比例",
            min_value=0.0,
            max_value=0.5,
            value=current_config.get("max_single_trade_rate", 0.20),
            step=0.05,
            format="%.0f%%",
            help="单笔交易金额不超过总资金的比例（默认20%）"
        )

        st.markdown("---")
        st.markdown("#### 第6层：异常交易频率")
        st.info("限制单位时间内的交易次数，防止策略失控")

        max_trades_per_hour = st.number_input(
            "每小时最大交易次数",
            min_value=1,
            max_value=100,
            value=current_config.get("max_trades_per_hour", 20),
            step=1,
            help="单个策略每小时最多交易次数（默认20次）"
        )

        st.markdown("---")
        st.markdown("#### 第7层：涨跌停板检测")
        st.info("禁止在涨跌停板交易，避免买入无法卖出")

        enable_limit_check = st.checkbox(
            "启用涨跌停检测",
            value=current_config.get("enable_limit_check", True),
            help="检测股票是否涨停/跌停，禁止交易"
        )

        limit_threshold = st.slider(
            "涨跌停阈值",
            min_value=0.08,
            max_value=0.20,
            value=current_config.get("limit_threshold", 0.095),
            step=0.005,
            format="%.1f%%",
            help="涨跌幅≥此阈值视为涨跌停（普通股9.5%，ST 4.5%）"
        )

        # 提交按钮
        submitted = st.form_submit_button("💾 保存配置", type="primary", use_container_width=True)

        if submitted:
            try:
                update_response = requests.put(
                    f"{API_BASE_URL}/risk/config",
                    json={
                        "total_capital": total_capital,
                        "max_total_loss_rate": max_total_loss_rate,
                        "max_daily_loss_rate": max_daily_loss_rate,
                        "max_strategy_capital_rate": max_strategy_capital_rate,
                        "max_single_trade_rate": max_single_trade_rate,
                        "max_trades_per_hour": max_trades_per_hour,
                        "enable_limit_check": enable_limit_check,
                        "limit_threshold": limit_threshold
                    }
                )

                if update_response.status_code == 200:
                    st.success("✅ 风控配置已保存")
                    st.rerun()
                else:
                    st.error(f"保存失败: {update_response.text}")

            except requests.exceptions.RequestException as e:
                st.error(f"请求失败: {e}")

    # 当前配置预览
    with st.expander("📋 当前配置预览"):
        if current_config:
            col1, col2 = st.columns(2)

            with col1:
                st.metric("总资金", f"¥{current_config.get('total_capital', 0):,.0f}")
                st.metric("总止损", f"{current_config.get('max_total_loss_rate', 0):.0%}")
                st.metric("日止损", f"{current_config.get('max_daily_loss_rate', 0):.0%}")
                st.metric("单策略占用", f"{current_config.get('max_strategy_capital_rate', 0):.0%}")

            with col2:
                st.metric("单笔限制", f"{current_config.get('max_single_trade_rate', 0):.0%}")
                st.metric("小时交易次数", current_config.get("max_trades_per_hour", 0))
                st.metric("涨跌停检测", "✅ 启用" if current_config.get("enable_limit_check") else "❌ 关闭")
                st.metric("涨跌停阈值", f"{current_config.get('limit_threshold', 0):.1%}")

with tab2:
    st.markdown("### 🚫 黑名单管理")

    st.info("添加到黑名单的股票将禁止交易（如ST股票、退市警告等）")

    # 获取黑名单
    try:
        blacklist_response = requests.get(f"{API_BASE_URL}/risk/blacklist")

        if blacklist_response.status_code == 200:
            blacklist = blacklist_response.json().get("data", [])
        else:
            blacklist = []
            st.warning("无法获取黑名单")

    except requests.exceptions.RequestException as e:
        blacklist = []
        st.error(f"请求失败: {e}")

    # 添加黑名单
    col_add1, col_add2 = st.columns([3, 1])

    with col_add1:
        new_symbol = st.text_input(
            "股票代码",
            placeholder="如: SH600000, SZ000001",
            help="支持多个，逗号分隔"
        )

    with col_add2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ 添加", use_container_width=True):
            if new_symbol:
                symbols = [s.strip() for s in new_symbol.split(",") if s.strip()]

                try:
                    add_response = requests.post(
                        f"{API_BASE_URL}/risk/blacklist/add",
                        json={"symbols": symbols}
                    )

                    if add_response.status_code == 200:
                        st.success(f"✅ 已添加 {len(symbols)} 个股票到黑名单")
                        st.rerun()
                    else:
                        st.error(f"添加失败: {add_response.text}")

                except requests.exceptions.RequestException as e:
                    st.error(f"请求失败: {e}")

    # 黑名单列表
    st.markdown("---")
    st.markdown("#### 📋 黑名单列表")

    if blacklist:
        # 创建表格
        for idx, item in enumerate(blacklist):
            col_item1, col_item2, col_item3 = st.columns([2, 3, 1])

            with col_item1:
                st.text(item.get("symbol", "N/A"))

            with col_item2:
                st.caption(f"添加时间: {item.get('added_at', 'N/A')}")

            with col_item3:
                if st.button("🗑️", key=f"delete_blacklist_{idx}"):
                    try:
                        delete_response = requests.delete(
                            f"{API_BASE_URL}/risk/blacklist/{item['symbol']}"
                        )

                        if delete_response.status_code == 200:
                            st.success("✅ 已移除")
                            st.rerun()
                        else:
                            st.error("移除失败")

                    except requests.exceptions.RequestException as e:
                        st.error(f"请求失败: {e}")

        # 批量操作
        st.markdown("---")
        if st.button("🗑️ 清空黑名单", type="secondary"):
            if st.session_state.get("confirm_clear_blacklist"):
                # 执行清空
                for item in blacklist:
                    try:
                        requests.delete(f"{API_BASE_URL}/risk/blacklist/{item['symbol']}")
                    except:
                        pass

                st.success("✅ 黑名单已清空")
                st.session_state["confirm_clear_blacklist"] = False
                st.rerun()
            else:
                st.session_state["confirm_clear_blacklist"] = True
                st.warning("⚠️ 再次点击确认清空")

    else:
        st.info("黑名单为空")

with tab3:
    st.markdown("### 📊 风控日志")

    st.info("记录所有被风控拦截的交易")

    # 获取风控日志
    try:
        logs_response = requests.get(f"{API_BASE_URL}/risk/logs", params={"limit": 50})

        if logs_response.status_code == 200:
            logs = logs_response.json().get("data", [])

            if logs:
                # 统计
                stat_col1, stat_col2, stat_col3 = st.columns(3)

                with stat_col1:
                    st.metric("今日拦截", len([l for l in logs if l.get("date") == datetime.now().strftime("%Y-%m-%d")]))

                with stat_col2:
                    st.metric("总拦截", len(logs))

                with stat_col3:
                    most_common_reason = max(set([l.get("reason") for l in logs]), key=[l.get("reason") for l in logs].count) if logs else "N/A"
                    st.metric("主要原因", most_common_reason)

                st.markdown("---")

                # 日志列表
                for log in logs[:20]:  # 显示最近20条
                    risk_score = log.get("risk_score", 0)

                    # 根据风险评分选择颜色
                    if risk_score >= 80:
                        icon = "🔴"
                    elif risk_score >= 50:
                        icon = "🟡"
                    else:
                        icon = "🟢"

                    with st.expander(
                        f"{icon} {log.get('timestamp', 'N/A')} | "
                        f"{log.get('symbol', 'N/A')} | "
                        f"{log.get('reason', 'N/A')}"
                    ):
                        log_col1, log_col2 = st.columns(2)

                        with log_col1:
                            st.text(f"股票: {log.get('symbol', 'N/A')}")
                            st.text(f"方向: {log.get('action', 'N/A')}")
                            st.text(f"金额: ¥{log.get('amount', 0):,.2f}")

                        with log_col2:
                            st.text(f"风险评分: {risk_score}")
                            st.text(f"拦截原因: {log.get('reason', 'N/A')}")
                            st.text(f"策略ID: {log.get('strategy_id', 'N/A')}")

                # 下载日志
                if st.button("📥 下载风控日志"):
                    import pandas as pd

                    df_logs = pd.DataFrame(logs)
                    csv = df_logs.to_csv(index=False).encode('utf-8')

                    st.download_button(
                        label="下载CSV",
                        data=csv,
                        file_name=f"risk_logs_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )

            else:
                st.info("暂无风控日志")
        else:
            st.error("无法获取风控日志")

    except requests.exceptions.RequestException as e:
        st.error(f"请求失败: {e}")

# 使用说明
with st.expander("💡 使用说明"):
    st.markdown("""
    ### 7层风控说明

    1. **总资金止损** (10%)
       - 累计亏损达到总资金的10%时，停止所有交易
       - 保护本金，避免重大损失

    2. **黑名单股票**
       - 禁止交易指定股票
       - 建议添加ST、*ST、退市警告等股票

    3. **单日亏损限制** (5%)
       - 单日亏损达到5%时，当天停止交易
       - 防止单日暴亏

    4. **单策略资金占用** (30%)
       - 单个策略最多使用30%总资金
       - 分散风险，避免单策略失控

    5. **单笔交易限制** (20%)
       - 单笔交易不超过总资金20%
       - 防止单笔重仓

    6. **异常交易频率** (20次/小时)
       - 限制交易频率
       - 防止策略失控频繁交易

    7. **涨跌停板检测**
       - 禁止在涨跌停板交易
       - 避免买入后无法卖出

    ### 配置建议

    - 💡 小资金(<10万): 可适当放宽限制
    - 💡 大资金(>50万): 建议收紧风控参数
    - 💡 定期根据实际情况调整配置
    - 💡 密切关注风控日志，及时发现异常

    ### 黑名单建议

    建议添加以下类型股票：
    - ST、*ST股票（风险警示）
    - 退市警告股票
    - 长期停牌股票
    - 流动性极差的股票
    """)

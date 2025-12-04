"""
回测分析页面
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="回测分析", page_icon="📊", layout="wide")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.title("📊 回测分析")
st.markdown("在历史数据上验证策略表现，完整模拟A股市场规则")

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

strategies = get_strategies()

# 回测配置
st.markdown("### ⚙️ 回测配置")

col1, col2 = st.columns(2)

with col1:
    # 选择策略
    if strategies:
        strategy_options = {f"{s['name']} (ID: {s['id']})": s['id'] for s in strategies}
        selected_strategy_name = st.selectbox(
            "选择策略",
            options=list(strategy_options.keys()),
            help="选择要回测的策略"
        )
        selected_strategy_id = strategy_options[selected_strategy_name]

        # 显示策略代码
        selected_strategy = next((s for s in strategies if s['id'] == selected_strategy_id), None)
        if selected_strategy:
            with st.expander("📝 查看策略代码"):
                st.code(selected_strategy.get("code", ""), language="python")
    else:
        st.warning("暂无可用策略，请先生成策略")
        selected_strategy_id = None

    # 股票代码
    symbol = st.text_input(
        "股票代码",
        value="SH600000",
        help="格式：SH600000（上交所）、SZ000001（深交所）"
    )

    # 初始资金
    initial_cash = st.number_input(
        "初始资金（元）",
        min_value=10000,
        max_value=10000000,
        value=100000,
        step=10000,
        help="回测的初始资金"
    )

with col2:
    # 日期范围
    default_end = datetime.now()
    default_start = default_end - timedelta(days=365)

    start_date = st.date_input(
        "开始日期",
        value=default_start,
        help="回测开始日期"
    )

    end_date = st.date_input(
        "结束日期",
        value=default_end,
        help="回测结束日期"
    )

    # A股规则开关
    enable_china_rules = st.checkbox(
        "启用A股市场规则",
        value=True,
        help="包括T+1、涨跌停、印花税、佣金等"
    )

    # 快速回测选项
    st.markdown("**快速回测**")
    quick_col1, quick_col2 = st.columns(2)

    with quick_col1:
        if st.button("最近30天", use_container_width=True):
            end_date = datetime.now().date()
            start_date = (datetime.now() - timedelta(days=30)).date()
            st.rerun()

    with quick_col2:
        if st.button("最近90天", use_container_width=True):
            end_date = datetime.now().date()
            start_date = (datetime.now() - timedelta(days=90)).date()
            st.rerun()

# 运行回测
st.markdown("---")

if st.button("🚀 开始回测", type="primary", use_container_width=True, disabled=not selected_strategy_id):
    if not selected_strategy_id:
        st.error("请先选择策略")
    elif not symbol:
        st.error("请输入股票代码")
    else:
        with st.spinner("⏳ 回测运行中，请稍候..."):
            try:
                # 调用回测API
                response = requests.post(
                    f"{API_BASE_URL}/backtest/run",
                    json={
                        "strategy_id": selected_strategy_id,
                        "symbol": symbol,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "initial_cash": initial_cash,
                        "enable_china_rules": enable_china_rules
                    },
                    timeout=300
                )

                if response.status_code == 200:
                    result = response.json().get("data", {})

                    st.success("✅ 回测完成！")

                    # 性能指标
                    st.markdown("### 📈 性能指标")

                    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

                    with metric_col1:
                        annual_return = result.get("annual_return", 0)
                        st.metric(
                            "年化收益率",
                            f"{annual_return:.2%}",
                            delta=f"{annual_return:.2%}",
                            delta_color="normal"
                        )

                    with metric_col2:
                        sharpe = result.get("sharpe_ratio", 0)
                        st.metric(
                            "夏普比率",
                            f"{sharpe:.2f}",
                            help="风险调整后收益，>1为良好，>2为优秀"
                        )

                    with metric_col3:
                        max_dd = result.get("max_drawdown", 0)
                        st.metric(
                            "最大回撤",
                            f"{max_dd:.2%}",
                            delta=f"-{max_dd:.2%}",
                            delta_color="inverse"
                        )

                    with metric_col4:
                        win_rate = result.get("win_rate", 0)
                        st.metric(
                            "胜率",
                            f"{win_rate:.2%}",
                            help="盈利交易占比"
                        )

                    st.markdown("---")

                    # 更多指标
                    detail_col1, detail_col2, detail_col3 = st.columns(3)

                    with detail_col1:
                        st.metric("总交易次数", result.get("total_trades", 0))
                        st.metric("盈利次数", result.get("profit_trades", 0))

                    with detail_col2:
                        st.metric("总收益", f"¥{result.get('total_return', 0):,.2f}")
                        st.metric("波动率", f"{result.get('volatility', 0):.2%}")

                    with detail_col3:
                        st.metric("最终资产", f"¥{result.get('final_value', 0):,.2f}")
                        st.metric("收益/回撤比", f"{result.get('return_over_drawdown', 0):.2f}")

                    # 资金曲线图
                    if result.get("equity_curve"):
                        st.markdown("### 📉 资金曲线")

                        equity_data = result["equity_curve"]
                        df_equity = pd.DataFrame(equity_data)

                        fig = go.Figure()

                        fig.add_trace(go.Scatter(
                            x=df_equity.get("date", df_equity.index),
                            y=df_equity["value"],
                            mode='lines',
                            name='策略净值',
                            line=dict(color='#1f77b4', width=2)
                        ))

                        # 添加基准线（初始资金）
                        fig.add_hline(
                            y=initial_cash,
                            line_dash="dash",
                            line_color="gray",
                            annotation_text="初始资金"
                        )

                        fig.update_layout(
                            title="策略资金曲线",
                            xaxis_title="日期",
                            yaxis_title="资金（元）",
                            hovermode='x unified',
                            height=400
                        )

                        st.plotly_chart(fig, use_container_width=True)

                    # 交易记录
                    if result.get("trades"):
                        st.markdown("### 📋 交易记录")

                        trades_df = pd.DataFrame(result["trades"])

                        # 显示前10条
                        st.dataframe(
                            trades_df.head(10),
                            use_container_width=True,
                            hide_index=True
                        )

                        # 下载完整记录
                        csv = trades_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 下载完整交易记录",
                            data=csv,
                            file_name=f"trades_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )

                    # A股规则验证
                    if enable_china_rules and result.get("china_rules_applied"):
                        st.markdown("### 🇨🇳 A股规则应用")

                        rules_col1, rules_col2 = st.columns(2)

                        with rules_col1:
                            st.info("✅ T+1制度已应用")
                            st.info("✅ 涨跌停限制已检查")
                            st.info("✅ 印花税已计算（0.1%）")

                        with rules_col2:
                            st.info("✅ 佣金已计算（0.03%，最低¥5）")
                            st.info("✅ 停牌检测已启用")
                            st.info("✅ 交易单位已验证（100股整数倍）")

                else:
                    st.error(f"❌ 回测失败: {response.status_code}")
                    st.error(response.text)

            except requests.exceptions.Timeout:
                st.error("⏱️ 回测超时，请缩短回测周期或稍后重试")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ 请求失败: {e}")
            except Exception as e:
                st.error(f"❌ 发生错误: {e}")

# 历史回测记录
st.markdown("---")
st.markdown("### 📚 历史回测记录")

try:
    history_response = requests.get(f"{API_BASE_URL}/backtest/results", params={"limit": 5})

    if history_response.status_code == 200:
        history = history_response.json().get("data", [])

        if history:
            for record in history:
                with st.expander(
                    f"📊 策略ID {record.get('strategy_id')} | "
                    f"{record.get('start_date')} ~ {record.get('end_date')} | "
                    f"收益: {record.get('annual_return', 0):.2%}"
                ):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("年化收益", f"{record.get('annual_return', 0):.2%}")
                        st.metric("夏普比率", f"{record.get('sharpe_ratio', 0):.2f}")

                    with col2:
                        st.metric("最大回撤", f"{record.get('max_drawdown', 0):.2%}")
                        st.metric("胜率", f"{record.get('win_rate', 0):.2%}")

                    with col3:
                        st.metric("总交易", record.get("total_trades", 0))
                        st.text(f"执行时间: {record.get('executed_at', 'N/A')}")
        else:
            st.info("暂无历史回测记录")
except:
    st.warning("无法加载历史记录")

# 使用说明
with st.expander("💡 使用说明"):
    st.markdown("""
    ### A股市场规则说明

    系统完整实现以下8条A股规则：

    1. **停牌检测**: 成交量为0时视为停牌，不可交易
    2. **涨跌停限制**:
       - 普通股票: ±10%
       - ST股票: ±5%
       - 科创板/创业板: ±20%
    3. **T+1制度**: 当日买入的股票不可当日卖出
    4. **最小交易单位**: 买入必须是100股整数倍，卖出允许零股
    5. **印花税**: 卖出时收取0.1%，买入免税
    6. **佣金**: 双向收取0.03%，最低¥5
    7. **滑点**: 估算0.1%滑点
    8. **仓位/资金管理**: 限制最大持仓和单笔交易金额

    ### 性能指标说明

    - **年化收益率**: 策略的年化投资回报率
    - **夏普比率**: 风险调整后收益，>1良好，>2优秀
    - **最大回撤**: 从峰值到谷底的最大跌幅
    - **胜率**: 盈利交易占总交易的比例
    - **波动率**: 收益的标准差，衡量风险

    ### 注意事项

    - ⚠️ 回测使用历史数据，不代表未来表现
    - ⚠️ 实盘滑点可能大于回测估算值
    - ⚠️ 建议在多个时间段、多只股票上回测验证
    """)

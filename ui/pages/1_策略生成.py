"""
策略生成页面
"""
import streamlit as st
import requests
import json
from datetime import datetime
import os

st.set_page_config(page_title="策略生成", page_icon="🧠", layout="wide")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.title("🧠 AI策略生成")
st.markdown("使用自然语言描述您的交易想法，AI将自动生成可执行的策略代码")

# 两列布局
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📝 策略描述")

    # 预设示例
    example_prompts = {
        "双均线策略": "双均线策略，MA5/MA20金叉买入，死叉卖出",
        "布林带突破": "布林带突破策略，价格突破上轨买入，跌破下轨卖出",
        "MACD+RSI": "MACD金叉且RSI<30时买入，MACD死叉或RSI>70时卖出",
        "自定义": ""
    }

    selected_example = st.selectbox(
        "选择示例策略",
        options=list(example_prompts.keys()),
        help="选择预设示例或自定义策略"
    )

    user_input = st.text_area(
        "策略描述",
        value=example_prompts[selected_example],
        height=150,
        placeholder="请用自然语言描述您的策略思路...\n\n示例：\n- 双均线策略，MA5上穿MA20买入\n- 当RSI<30且MACD金叉时买入\n- 价格突破20日最高价买入",
        help="尽量详细描述策略逻辑、入场条件、出场条件"
    )

    # 高级选项
    with st.expander("⚙️ 高级选项"):
        context_symbol = st.text_input(
            "目标股票",
            value="SH600000",
            help="可选，指定策略适用的股票代码"
        )

        context_timeframe = st.selectbox(
            "时间周期",
            ["1天", "1周", "1月"],
            help="策略运行的时间周期"
        )

        enable_stop_loss = st.checkbox("启用止损", value=True)
        if enable_stop_loss:
            stop_loss_pct = st.slider("止损百分比", 1, 20, 10, 1, help="单位：%")

    # 生成按钮
    generate_button = st.button("🚀 生成策略", type="primary", use_container_width=True)

with col2:
    st.markdown("### 📋 生成结果")

    if generate_button:
        if not user_input.strip():
            st.error("请先输入策略描述")
        else:
            with st.spinner("🤖 AI正在生成策略代码..."):
                try:
                    # 构建上下文
                    context = {}
                    if context_symbol:
                        context["symbol"] = context_symbol
                    if enable_stop_loss:
                        context["stop_loss"] = stop_loss_pct / 100

                    # 调用API
                    response = requests.post(
                        f"{API_BASE_URL}/strategies/generate",
                        json={"user_input": user_input, "context": context},
                        timeout=180  # AI生成可能需要较长时间
                    )

                    if response.status_code == 200:
                        result = response.json()
                        data = result.get("data", {})

                        st.success("✅ 策略生成成功！")

                        # 显示策略信息
                        st.markdown(f"**策略名称**: {data.get('name', 'N/A')}")
                        st.markdown(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                        # 显示策略代码
                        st.markdown("#### 策略代码")
                        st.code(data.get("code", ""), language="python")

                        # 显示参数
                        if data.get("params"):
                            st.markdown("#### 策略参数")
                            st.json(data["params"])

                        # 安全检查结果
                        if data.get("security_check"):
                            security = data["security_check"]
                            if security.get("safe"):
                                st.success(f"🔒 安全检查通过: {security.get('message', '')}")
                            else:
                                st.error(f"⚠️ 安全检查失败: {security.get('message', '')}")
                                if security.get("details"):
                                    st.json(security["details"])

                        # 保存策略选项
                        st.markdown("---")
                        col_save1, col_save2 = st.columns(2)

                        with col_save1:
                            if st.button("💾 保存策略", use_container_width=True):
                                # 保存策略到数据库
                                save_response = requests.post(
                                    f"{API_BASE_URL}/strategies",
                                    json={
                                        "name": data.get("name"),
                                        "code": data.get("code"),
                                        "params": data.get("params", {}),
                                        "status": "draft"
                                    }
                                )

                                if save_response.status_code == 200:
                                    st.success("✅ 策略已保存")
                                    saved_data = save_response.json()
                                    st.info(f"策略ID: {saved_data.get('id')}")
                                else:
                                    st.error(f"保存失败: {save_response.text}")

                        with col_save2:
                            if st.button("📊 立即回测", use_container_width=True):
                                st.info("请先保存策略，然后前往回测页面")

                    else:
                        st.error(f"❌ 生成失败: {response.status_code}")
                        st.error(response.text)

                except requests.exceptions.Timeout:
                    st.error("⏱️ 请求超时，AI生成时间较长，请重试")
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ 请求失败: {e}")
                except Exception as e:
                    st.error(f"❌ 发生错误: {e}")

# 分隔线
st.markdown("---")

# 策略列表
st.markdown("### 📚 已保存的策略")

# 获取策略列表
try:
    list_response = requests.get(f"{API_BASE_URL}/strategies", params={"limit": 10})

    if list_response.status_code == 200:
        strategies = list_response.json().get("data", [])

        if strategies:
            # 创建表格显示
            for strategy in strategies:
                with st.expander(f"📝 {strategy.get('name', 'Unnamed')} (ID: {strategy.get('id')})"):
                    col_info1, col_info2, col_info3 = st.columns(3)

                    with col_info1:
                        st.metric("状态", strategy.get("status", "N/A"))

                    with col_info2:
                        annual_return = strategy.get("annual_return")
                        if annual_return is not None:
                            st.metric("年化收益", f"{annual_return:.2%}")
                        else:
                            st.metric("年化收益", "--")

                    with col_info3:
                        sharpe = strategy.get("sharpe_ratio")
                        if sharpe is not None:
                            st.metric("夏普比率", f"{sharpe:.2f}")
                        else:
                            st.metric("夏普比率", "--")

                    # 操作按钮
                    btn_col1, btn_col2, btn_col3 = st.columns(3)

                    with btn_col1:
                        if st.button("📊 回测", key=f"backtest_{strategy['id']}"):
                            st.info("请前往回测页面")

                    with btn_col2:
                        if st.button("👁️ 查看代码", key=f"view_{strategy['id']}"):
                            st.code(strategy.get("code", ""), language="python")

                    with btn_col3:
                        if st.button("🗑️ 删除", key=f"delete_{strategy['id']}"):
                            delete_response = requests.delete(
                                f"{API_BASE_URL}/strategies/{strategy['id']}"
                            )
                            if delete_response.status_code == 200:
                                st.success("✅ 已删除")
                                st.rerun()
                            else:
                                st.error("❌ 删除失败")
        else:
            st.info("暂无保存的策略")
    else:
        st.warning("无法获取策略列表")

except requests.exceptions.RequestException as e:
    st.warning(f"无法连接到API服务: {e}")

# 使用提示
with st.expander("💡 使用提示"):
    st.markdown("""
    ### 如何描述策略？

    **好的描述示例**:
    - ✅ "双均线策略，5日均线上穿20日均线时买入，下穿时卖出"
    - ✅ "当RSI指标低于30且MACD金叉时买入，RSI高于70时卖出"
    - ✅ "布林带策略，价格突破上轨买入，跌破中轨止损"

    **不好的描述**:
    - ❌ "帮我赚钱" （过于模糊）
    - ❌ "买入股票" （缺少具体条件）
    - ❌ "最好的策略" （没有指标说明）

    ### 策略安全检查

    系统会自动检查生成的代码：
    - 🔍 语法检查
    - 🚫 危险函数检测（eval/exec/os等）
    - 📊 圈复杂度限制（≤20）
    - ✅ 必需方法检查（on_bar等）

    ### 下一步

    1. 生成策略后，点击"保存策略"
    2. 前往"回测分析"页面验证策略表现
    3. 表现良好的策略可加入影子账户观察
    """)

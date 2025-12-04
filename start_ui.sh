#!/bin/bash
# CN5-Lite Streamlit UI 启动脚本

echo "🚀 启动CN5-Lite Streamlit界面..."

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "⚠️  未找到虚拟环境，正在创建..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "⚠️  未找到.env文件，正在复制模板..."
    cp .env.example .env
    echo "请编辑.env文件配置API密钥"
    exit 1
fi

# 设置API基础URL（默认本地）
export API_BASE_URL=${API_BASE_URL:-"http://localhost:8000/api/v1"}

# 启动Streamlit
echo "📱 Streamlit界面启动中..."
echo "🌐 访问地址: http://localhost:8501"
echo "🔗 API地址: $API_BASE_URL"
echo ""
echo "按Ctrl+C停止服务"
echo ""

streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0

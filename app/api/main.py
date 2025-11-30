"""
CN5-Lite FastAPI主应用

提供RESTful API接口
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.logger import get_logger
from app.config import Config

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("CN5-Lite API启动")
    config = Config()
    logger.info(f"配置加载完成", env=config.ENVIRONMENT)

    yield

    # 关闭时
    logger.info("CN5-Lite API关闭")


# 创建FastAPI应用
app = FastAPI(
    title="CN5-Lite AI量化交易系统",
    description="基于AI的A股量化交易系统API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "CN5-Lite API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }


# 导入路由
from app.api.routes import strategy, backtest, trading, shadow, risk

# 注册路由
app.include_router(strategy.router, prefix="/api/v1/strategies", tags=["策略管理"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["回测"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["交易管理"])
app.include_router(shadow.router, prefix="/api/v1/shadow", tags=["影子账户"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["风控"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

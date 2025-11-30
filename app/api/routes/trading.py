"""
交易管理API路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.ai_trading_manager import AITradingManager
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 全局交易管理器
trading_manager = AITradingManager()


# ==================
# 请求/响应模型
# ==================

class TradingStartRequest(BaseModel):
    """启动交易请求"""
    strategy_id: int
    require_approval: Optional[bool] = False
    auto_approve_threshold: Optional[float] = 3000


class TradeExecuteRequest(BaseModel):
    """执行交易请求"""
    strategy_id: int
    action: str
    symbol: str
    amount: int
    price: float


# ==================
# API端点
# ==================

@router.post("/start")
async def start_trading(request: TradingStartRequest):
    """
    启动自动交易

    Args:
        request: 启动参数

    Returns:
        启动结果
    """
    try:
        # 获取策略
        from app.services.ai_generator import StrategyStorage
        storage = StrategyStorage()
        strategy = storage.load(request.strategy_id)

        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")

        # 添加策略到管理器
        trading_manager.add_strategy(
            strategy_id=request.strategy_id,
            strategy_code=strategy['code']
        )

        # 启动交易
        result = trading_manager.start_auto_trading()

        logger.info(f"交易启动", strategy_id=request.strategy_id)

        return {
            "success": True,
            "message": "交易已启动",
            "strategy_id": request.strategy_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动交易失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_trading():
    """
    停止自动交易

    Returns:
        停止结果
    """
    try:
        result = trading_manager.stop_auto_trading()

        logger.info("交易已停止")

        return {
            "success": True,
            "message": "交易已停止"
        }

    except Exception as e:
        logger.error(f"停止交易失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_trading_status():
    """
    获取交易状态

    Returns:
        交易状态
    """
    return {
        "success": True,
        "data": {
            "is_running": trading_manager.is_running,
            "strategies": trading_manager.list_strategies()
        }
    }


@router.get("/trades/{strategy_id}")
async def get_trades(strategy_id: int):
    """
    获取交易记录

    Args:
        strategy_id: 策略ID

    Returns:
        交易记录
    """
    try:
        trades = trading_manager.get_trades(strategy_id)

        return {
            "success": True,
            "data": trades,
            "total": len(trades)
        }

    except Exception as e:
        logger.error(f"获取交易记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_trade(request: TradeExecuteRequest):
    """
    手动执行交易

    Args:
        request: 交易请求

    Returns:
        执行结果
    """
    try:
        signal = {
            'strategy_id': request.strategy_id,
            'action': request.action,
            'symbol': request.symbol,
            'amount': request.amount,
            'price': request.price
        }

        result = trading_manager.execute_trade(signal)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"执行交易失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rehydrate/{strategy_id}")
async def rehydrate_strategy(strategy_id: int):
    """
    恢复策略状态（容器重启后）

    Args:
        strategy_id: 策略ID

    Returns:
        恢复结果
    """
    try:
        result = trading_manager.rehydrate_state(strategy_id)

        logger.info(f"策略状态恢复完成", strategy_id=strategy_id)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"恢复策略状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
风控API路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.risk_validator import RiskValidator
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 全局风控验证器
risk_validator = RiskValidator(total_capital=100000)


# ==================
# 请求/响应模型
# ==================

class RiskValidateRequest(BaseModel):
    """风控验证请求"""
    action: str
    symbol: str
    amount: int
    price: float
    strategy_id: Optional[int] = 1


class RiskConfigUpdateRequest(BaseModel):
    """风控配置更新请求"""
    total_capital: Optional[float] = None
    max_total_loss_rate: Optional[float] = None
    max_daily_loss_rate: Optional[float] = None
    max_strategy_capital_rate: Optional[float] = None
    max_single_trade_rate: Optional[float] = None


# ==================
# API端点
# ==================

@router.post("/validate")
async def validate_trade(request: RiskValidateRequest):
    """
    验证交易

    Args:
        request: 交易信号

    Returns:
        验证结果
    """
    try:
        signal = {
            'action': request.action,
            'symbol': request.symbol,
            'amount': request.amount,
            'price': request.price,
            'strategy_id': request.strategy_id
        }

        result = risk_validator.validate(signal)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"风控验证失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_risk_config():
    """
    获取风控配置

    Returns:
        当前配置
    """
    return {
        "success": True,
        "data": {
            "total_capital": risk_validator.total_capital,
            "max_total_loss_rate": risk_validator.max_total_loss_rate,
            "max_daily_loss_rate": risk_validator.max_daily_loss_rate,
            "max_strategy_capital_rate": risk_validator.max_strategy_capital_rate,
            "max_single_trade_rate": risk_validator.max_single_trade_rate,
            "max_trades_per_hour": risk_validator.max_trades_per_hour
        }
    }


@router.put("/config")
async def update_risk_config(request: RiskConfigUpdateRequest):
    """
    更新风控配置

    Args:
        request: 新配置

    Returns:
        更新结果
    """
    try:
        if request.total_capital is not None:
            risk_validator.total_capital = request.total_capital

        if request.max_total_loss_rate is not None:
            risk_validator.max_total_loss_rate = request.max_total_loss_rate

        if request.max_daily_loss_rate is not None:
            risk_validator.max_daily_loss_rate = request.max_daily_loss_rate

        if request.max_strategy_capital_rate is not None:
            risk_validator.max_strategy_capital_rate = request.max_strategy_capital_rate

        if request.max_single_trade_rate is not None:
            risk_validator.max_single_trade_rate = request.max_single_trade_rate

        logger.info("风控配置已更新")

        return {
            "success": True,
            "message": "配置已更新"
        }

    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/account/update")
async def update_account_value(current_value: float):
    """
    更新账户价值

    Args:
        current_value: 当前账户价值

    Returns:
        更新结果
    """
    try:
        risk_validator.update_account_value(current_value)

        return {
            "success": True,
            "message": "账户价值已更新"
        }

    except Exception as e:
        logger.error(f"更新账户价值失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blacklist")
async def get_blacklist():
    """
    获取黑名单

    Returns:
        黑名单列表
    """
    return {
        "success": True,
        "data": {
            "blacklist": list(risk_validator.blacklist),
            "st_keywords": risk_validator.st_keywords
        }
    }


@router.post("/blacklist/add")
async def add_to_blacklist(symbol: str):
    """
    添加到黑名单

    Args:
        symbol: 股票代码

    Returns:
        添加结果
    """
    try:
        risk_validator.blacklist.add(symbol)

        logger.info(f"添加到黑名单", symbol=symbol)

        return {
            "success": True,
            "message": f"{symbol}已添加到黑名单"
        }

    except Exception as e:
        logger.error(f"添加黑名单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/blacklist/{symbol}")
async def remove_from_blacklist(symbol: str):
    """
    从黑名单移除

    Args:
        symbol: 股票代码

    Returns:
        移除结果
    """
    try:
        if symbol in risk_validator.blacklist:
            risk_validator.blacklist.remove(symbol)

            logger.info(f"从黑名单移除", symbol=symbol)

            return {
                "success": True,
                "message": f"{symbol}已从黑名单移除"
            }
        else:
            raise HTTPException(status_code=404, detail="股票不在黑名单中")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除黑名单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

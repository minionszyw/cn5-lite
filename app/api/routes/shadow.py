"""
影子账户API路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.services.shadow_manager import ShadowManager
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 全局影子账户管理器
shadow_manager = ShadowManager()


# ==================
# 请求/响应模型
# ==================

class ShadowAccountCreateRequest(BaseModel):
    """创建影子账户请求"""
    strategy_id: int
    initial_cash: Optional[float] = 100000
    observation_days: Optional[int] = 7


# ==================
# API端点
# ==================

@router.post("/accounts")
async def create_shadow_account(request: ShadowAccountCreateRequest):
    """
    创建影子账户

    Args:
        request: 创建参数

    Returns:
        账户ID
    """
    try:
        account_id = shadow_manager.create_shadow_account(
            strategy_id=request.strategy_id,
            initial_cash=request.initial_cash,
            observation_days=request.observation_days
        )

        logger.info(f"影子账户创建成功", account_id=account_id)

        return {
            "success": True,
            "data": {
                "account_id": account_id
            }
        }

    except Exception as e:
        logger.error(f"创建影子账户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}")
async def get_shadow_account(account_id: int):
    """
    获取影子账户详情

    Args:
        account_id: 账户ID

    Returns:
        账户详情
    """
    account = shadow_manager.get_account(account_id)

    if not account:
        raise HTTPException(status_code=404, detail="影子账户不存在")

    return {
        "success": True,
        "data": account
    }


@router.get("/top")
async def get_top_strategies(limit: int = 3, min_score: float = 30.0):
    """
    获取Top N策略

    Args:
        limit: 返回数量
        min_score: 最低分数

    Returns:
        Top策略列表
    """
    try:
        top_strategies = shadow_manager.get_top_strategies(
            limit=limit,
            min_score=min_score
        )

        return {
            "success": True,
            "data": top_strategies,
            "total": len(top_strategies)
        }

    except Exception as e:
        logger.error(f"获取Top策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/{account_id}/promote")
async def promote_account(account_id: int):
    """
    晋升账户到实盘

    Args:
        account_id: 账户ID

    Returns:
        晋升结果
    """
    try:
        result = shadow_manager.promote_to_live(account_id)

        if not result:
            raise HTTPException(status_code=400, detail="不符合晋升条件")

        logger.info(f"影子账户晋升成功", account_id=account_id)

        return {
            "success": True,
            "message": "账户已晋升到实盘"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"晋升账户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/{account_id}/terminate")
async def terminate_account(account_id: int, reason: str = ""):
    """
    终止影子账户

    Args:
        account_id: 账户ID
        reason: 终止原因

    Returns:
        终止结果
    """
    try:
        shadow_manager.terminate_account(account_id, reason=reason)

        logger.info(f"影子账户已终止", account_id=account_id)

        return {
            "success": True,
            "message": "账户已终止"
        }

    except Exception as e:
        logger.error(f"终止账户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}/score")
async def get_account_score(account_id: int):
    """
    获取账户评分

    Args:
        account_id: 账户ID

    Returns:
        评分
    """
    try:
        score = shadow_manager.calculate_score(account_id)

        return {
            "success": True,
            "data": {
                "account_id": account_id,
                "score": score
            }
        }

    except Exception as e:
        logger.error(f"获取评分失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

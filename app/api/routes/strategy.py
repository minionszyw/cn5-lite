"""
策略管理API路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.ai_generator import AIStrategyGenerator, StrategyStorage
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 全局存储实例
storage = StrategyStorage()


# ==================
# 请求/响应模型
# ==================

class StrategyGenerateRequest(BaseModel):
    """策略生成请求"""
    user_input: str
    context: Optional[Dict[str, Any]] = None


class StrategyCreateRequest(BaseModel):
    """策略创建请求"""
    name: str
    code: str
    params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class StrategyResponse(BaseModel):
    """策略响应"""
    id: int
    name: str
    code: str
    params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    created_at: str


# ==================
# API端点
# ==================

@router.post("/generate")
async def generate_strategy(request: StrategyGenerateRequest):
    """
    AI生成策略

    Args:
        request: 生成请求

    Returns:
        生成的策略代码和元数据
    """
    try:
        # 从配置获取API密钥
        from app.config import Config
        config = Config()

        generator = AIStrategyGenerator(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_API_BASE_URL,
            model=config.AI_MODEL
        )

        result = generator.generate(
            user_input=request.user_input,
            context=request.context
        )

        logger.info("策略生成成功")

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"策略生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=StrategyResponse)
async def create_strategy(request: StrategyCreateRequest):
    """
    创建策略

    Args:
        request: 策略信息

    Returns:
        创建的策略
    """
    try:
        strategy_data = {
            "name": request.name,
            "code": request.code,
            "params": request.params or {},
            "description": request.description or ""
        }

        strategy_id = storage.save(strategy_data)

        # 加载完整信息
        saved_strategy = storage.load(strategy_id)

        logger.info(f"策略创建成功", strategy_id=strategy_id)

        return saved_strategy

    except Exception as e:
        logger.error(f"策略创建失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: int):
    """
    获取策略详情

    Args:
        strategy_id: 策略ID

    Returns:
        策略详情
    """
    strategy = storage.load(strategy_id)

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    return {
        "success": True,
        "data": strategy
    }


@router.get("/")
async def list_strategies(limit: int = 100, offset: int = 0):
    """
    列出所有策略

    Args:
        limit: 返回数量
        offset: 偏移量

    Returns:
        策略列表
    """
    try:
        strategies = storage.list(limit=limit, offset=offset)

        return {
            "success": True,
            "data": strategies,
            "total": len(strategies)
        }

    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int):
    """
    删除策略

    Args:
        strategy_id: 策略ID

    Returns:
        删除结果
    """
    try:
        storage.delete(strategy_id)

        logger.info(f"策略删除成功", strategy_id=strategy_id)

        return {
            "success": True,
            "message": "策略已删除"
        }

    except Exception as e:
        logger.error(f"策略删除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/validate")
async def validate_strategy(strategy_id: int):
    """
    验证策略代码

    Args:
        strategy_id: 策略ID

    Returns:
        验证结果
    """
    try:
        strategy = storage.load(strategy_id)

        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")

        from app.services.ai_generator import CodeSecurityChecker

        checker = CodeSecurityChecker()
        result = checker.check(strategy['code'])

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"策略验证失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

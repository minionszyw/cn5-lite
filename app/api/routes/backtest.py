"""
回测API路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import pandas as pd

from app.services.backtest_engine import BacktestEngine
from app.services.ai_generator import StrategyStorage
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

storage = StrategyStorage()


# ==================
# 请求/响应模型
# ==================

class BacktestRequest(BaseModel):
    """回测请求"""
    strategy_id: int
    symbol: str
    start_date: str
    end_date: str
    initial_cash: Optional[float] = 100000
    enable_china_rules: Optional[bool] = True


class BacktestResponse(BaseModel):
    """回测响应"""
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    final_value: float
    total_return: float


# ==================
# API端点
# ==================

@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """
    运行回测

    Args:
        request: 回测参数

    Returns:
        回测结果
    """
    try:
        # 1. 获取策略
        strategy = storage.load(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")

        # 2. 获取历史数据（这里简化，实际应该从数据源获取）
        from app.services.multi_datasource import DataSourceManager

        data_manager = DataSourceManager()
        data = data_manager.fetch(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date
        )

        if data is None or len(data) == 0:
            raise HTTPException(status_code=404, detail="无法获取历史数据")

        # 3. 运行回测
        engine = BacktestEngine(
            initial_cash=request.initial_cash,
            enable_china_rules=request.enable_china_rules
        )

        result = engine.run(
            strategy_code=strategy['code'],
            data=data,
            symbol=request.symbol,
            params=strategy.get('params')
        )

        logger.info(f"回测完成", strategy_id=request.strategy_id, trades=result['total_trades'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick")
async def quick_backtest(
    strategy_id: int,
    symbol: str = "SH600000",
    days: int = 30
):
    """
    快速回测（使用最近N天数据）

    Args:
        strategy_id: 策略ID
        symbol: 股票代码
        days: 天数

    Returns:
        回测结果
    """
    try:
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        request = BacktestRequest(
            strategy_id=strategy_id,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        return await run_backtest(request)

    except Exception as e:
        logger.error(f"快速回测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

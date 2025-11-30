"""
CN5-Lite 影子账户管理器

功能:
1. 创建影子账户
2. 多维度评分（年化收益30%、夏普25%、回撤20%、波动15%、胜率10%）
3. 时间权重（指数衰减，半衰期7天）
4. Top N策略筛选
5. 晋升条件判断
6. 历史数据回放
7. 按天分段回测
"""

import math
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.logger import get_logger
from app.errors import ValidationError
from app.services.backtest_engine import BacktestEngine

logger = get_logger(__name__)


# ==================
# 影子账户管理器
# ==================

class ShadowManager:
    """
    影子账户管理器

    功能:
    1. 管理多个影子账户
    2. 计算综合评分
    3. 筛选优质策略
    4. 晋升到实盘
    """

    def __init__(self):
        """初始化管理器"""
        self.accounts: Dict[int, Dict[str, Any]] = {}
        self.next_account_id = 1

        # 评分权重
        self.score_weights = {
            'annual_return': 0.30,      # 年化收益率 30%
            'sharpe_ratio': 0.25,       # 夏普比率 25%
            'max_drawdown': 0.20,       # 最大回撤 20%
            'volatility': 0.15,         # 波动率 15%
            'win_rate': 0.10            # 胜率 10%
        }

        # 晋升条件
        self.promotion_min_score = 35.0
        self.promotion_min_days = 14

        # 时间权重半衰期（天）
        self.time_decay_halflife = 7

        logger.info("影子账户管理器初始化完成")

    def create_shadow_account(
        self,
        strategy_id: int,
        initial_cash: float = 100000,
        observation_days: int = 7
    ) -> int:
        """
        创建影子账户

        Args:
            strategy_id: 策略ID
            initial_cash: 初始资金
            observation_days: 观察天数

        Returns:
            账户ID
        """
        account_id = self.next_account_id
        self.next_account_id += 1

        self.accounts[account_id] = {
            'id': account_id,
            'strategy_id': strategy_id,
            'initial_cash': initial_cash,
            'current_value': initial_cash,
            'observation_days': observation_days,
            'status': 'observing',  # observing/promoted/terminated
            'created_at': datetime.now().isoformat(),
            'metrics': {},
            'daily_records': [],
            'score': 0.0
        }

        logger.info(f"创建影子账户", account_id=account_id, strategy_id=strategy_id)

        return account_id

    def get_account(self, account_id: int) -> Optional[Dict[str, Any]]:
        """
        获取账户信息

        Args:
            account_id: 账户ID

        Returns:
            账户信息
        """
        return self.accounts.get(account_id)

    def update_account_metrics(self, account_id: int, metrics: Dict[str, float]):
        """
        更新账户指标

        Args:
            account_id: 账户ID
            metrics: 指标字典
        """
        if account_id not in self.accounts:
            raise ValidationError(f"账户不存在: {account_id}")

        self.accounts[account_id]['metrics'] = metrics

        # 重新计算评分
        score = self.calculate_score(account_id)
        self.accounts[account_id]['score'] = score

        logger.info(f"更新账户指标", account_id=account_id, score=score)

    def calculate_score(self, account_id: int) -> float:
        """
        计算综合评分

        Args:
            account_id: 账户ID

        Returns:
            评分（0-100）
        """
        if account_id not in self.accounts:
            raise ValidationError(f"账户不存在: {account_id}")

        account = self.accounts[account_id]
        metrics = account.get('metrics', {})

        if not metrics:
            return 0.0

        # 各维度归一化评分
        scores = {}

        # 年化收益率（0-100%映射到0-100分）
        annual_return = metrics.get('annual_return', 0)
        scores['annual_return'] = min(annual_return * 100, 100)

        # 夏普比率（0-3映射到0-100分）
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        scores['sharpe_ratio'] = min(sharpe_ratio / 3 * 100, 100)

        # 最大回撤（0-30%映射到100-0分，越小越好）
        max_drawdown = metrics.get('max_drawdown', 0)
        scores['max_drawdown'] = max(0, (0.30 - max_drawdown) / 0.30 * 100)

        # 波动率（0-30%映射到100-0分，越小越好）
        volatility = metrics.get('volatility', 0)
        scores['volatility'] = max(0, (0.30 - volatility) / 0.30 * 100)

        # 胜率（0-100%映射到0-100分）
        win_rate = metrics.get('win_rate', 0)
        scores['win_rate'] = win_rate * 100

        # 加权求和
        total_score = 0.0
        for metric, weight in self.score_weights.items():
            total_score += scores.get(metric, 0) * weight

        return round(total_score, 2)

    def _calculate_time_weight(self, days: int) -> float:
        """
        计算时间权重（指数衰减）

        Args:
            days: 距今天数

        Returns:
            权重（0-1）
        """
        # 指数衰减公式: weight = 0.5 ^ (days / halflife)
        return 0.5 ** (days / self.time_decay_halflife)

    def add_daily_record(self, account_id: int, record: Dict[str, Any]):
        """
        添加每日记录

        Args:
            account_id: 账户ID
            record: 每日记录
        """
        if account_id not in self.accounts:
            raise ValidationError(f"账户不存在: {account_id}")

        self.accounts[account_id]['daily_records'].append(record)

    def _calculate_weighted_return(self, account_id: int) -> float:
        """
        计算时间加权收益率

        Args:
            account_id: 账户ID

        Returns:
            加权收益率
        """
        if account_id not in self.accounts:
            return 0.0

        account = self.accounts[account_id]
        daily_records = account.get('daily_records', [])

        if not daily_records:
            return 0.0

        # 计算加权平均
        today = datetime.now()
        weighted_sum = 0.0
        weight_sum = 0.0

        for record in daily_records:
            record_date = datetime.strptime(record['date'], '%Y-%m-%d')
            days_ago = (today - record_date).days

            weight = self._calculate_time_weight(days_ago)
            weighted_sum += record.get('return', 0) * weight
            weight_sum += weight

        if weight_sum == 0:
            return 0.0

        return weighted_sum / weight_sum

    def get_top_strategies(
        self,
        limit: int = 3,
        min_score: float = 30.0
    ) -> List[Dict[str, Any]]:
        """
        获取Top N策略

        Args:
            limit: 返回数量
            min_score: 最低分数

        Returns:
            策略列表
        """
        # 筛选观察中的账户
        observing_accounts = [
            acc for acc in self.accounts.values()
            if acc['status'] == 'observing'
        ]

        # 过滤低分账户
        qualified_accounts = [
            acc for acc in observing_accounts
            if acc.get('score', 0) >= min_score
        ]

        # 按分数降序排列
        sorted_accounts = sorted(
            qualified_accounts,
            key=lambda x: x.get('score', 0),
            reverse=True
        )

        # 返回Top N
        return sorted_accounts[:limit]

    def check_promotion_eligibility(self, account_id: int) -> bool:
        """
        检查晋升资格

        Args:
            account_id: 账户ID

        Returns:
            是否符合晋升条件
        """
        if account_id not in self.accounts:
            return False

        account = self.accounts[account_id]

        # 条件1：分数 >= 35
        score = account.get('score', 0)
        if score < self.promotion_min_score:
            return False

        # 条件2：观察天数 >= 14
        observation_days = account.get('observation_days', 0)
        if observation_days < self.promotion_min_days:
            return False

        return True

    def promote_to_live(self, account_id: int) -> bool:
        """
        晋升到实盘

        Args:
            account_id: 账户ID

        Returns:
            是否成功
        """
        if not self.check_promotion_eligibility(account_id):
            logger.warning(f"不符合晋升条件", account_id=account_id)
            return False

        self.accounts[account_id]['status'] = 'promoted'
        self.accounts[account_id]['promoted_at'] = datetime.now().isoformat()

        logger.info(f"账户晋升到实盘", account_id=account_id)

        return True

    def update_observation_days(self, account_id: int, days: int):
        """
        更新观察天数

        Args:
            account_id: 账户ID
            days: 天数
        """
        if account_id in self.accounts:
            self.accounts[account_id]['observation_days'] = days

    def terminate_account(self, account_id: int, reason: str = ''):
        """
        终止账户

        Args:
            account_id: 账户ID
            reason: 终止原因
        """
        if account_id in self.accounts:
            self.accounts[account_id]['status'] = 'terminated'
            self.accounts[account_id]['terminated_at'] = datetime.now().isoformat()
            self.accounts[account_id]['termination_reason'] = reason

            logger.info(f"账户已终止", account_id=account_id, reason=reason)

    def replay_historical_data(
        self,
        account_id: int,
        strategy_code: str,
        data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        回放历史数据

        Args:
            account_id: 账户ID
            strategy_code: 策略代码
            data: 历史数据

        Returns:
            回测结果
        """
        if account_id not in self.accounts:
            raise ValidationError(f"账户不存在: {account_id}")

        account = self.accounts[account_id]
        initial_cash = account['initial_cash']

        # 使用回测引擎
        engine = BacktestEngine(initial_cash=initial_cash, enable_china_rules=True)

        # 执行回测
        result = engine.run(
            strategy_code=strategy_code,
            data=data,
            symbol='SH600000'  # 默认股票代码
        )

        # 更新账户指标
        self.update_account_metrics(account_id, result)

        logger.info(f"历史数据回放完成", account_id=account_id)

        return result

    def run_daily_backtest(
        self,
        account_id: int,
        strategy_code: str,
        data: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        按天分段回测

        Args:
            account_id: 账户ID
            strategy_code: 策略代码
            data: 历史数据

        Returns:
            每日结果列表
        """
        if account_id not in self.accounts:
            raise ValidationError(f"账户不存在: {account_id}")

        account = self.accounts[account_id]
        initial_cash = account['initial_cash']

        daily_results = []

        # 按天分段
        for i in range(len(data)):
            # 取从开始到当前天的数据
            day_data = data.iloc[:i+1].copy()

            if len(day_data) < 2:
                continue

            # 执行回测
            engine = BacktestEngine(initial_cash=initial_cash, enable_china_rules=True)

            result = engine.run(
                strategy_code=strategy_code,
                data=day_data,
                symbol='SH600000'
            )

            # 记录每日结果
            daily_result = {
                'date': str(day_data.iloc[-1]['date']),
                'value': result.get('final_value', initial_cash),
                'return': result.get('total_return', 0),
                'trades': result.get('total_trades', 0)
            }

            daily_results.append(daily_result)

            # 添加到账户记录
            self.add_daily_record(account_id, {
                'date': daily_result['date'],
                'return': daily_result['return']
            })

        logger.info(f"按天分段回测完成", account_id=account_id, days=len(daily_results))

        return daily_results

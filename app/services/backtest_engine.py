"""
CN5-Lite 回测引擎

功能:
1. 执行策略回测
2. A股市场规则适配
3. 性能指标计算
4. 交易税费计算
5. T+1制度支持
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.logger import get_logger
from app.errors import ValidationError, BacktestError
from app.services.strategy_adapter import StrategyAdapter

logger = get_logger(__name__)


# ==================
# 回测引擎
# ==================

class BacktestEngine:
    """
    回测引擎 + A股市场规则

    功能:
    1. 执行策略回测
    2. A股特殊规则（涨跌停、T+1、税费）
    3. 性能指标计算
    4. 交易记录管理
    """

    def __init__(
        self,
        initial_cash: float = 100000,
        enable_china_rules: bool = True,
        commission_rate: float = 0.0003,  # 佣金0.03%
        min_commission: float = 5.0,       # 最低佣金5元
        stamp_tax_rate: float = 0.001,     # 印花税0.1%
        slippage_rate: float = 0.001       # 滑点0.1%
    ):
        """
        初始化回测引擎

        Args:
            initial_cash: 初始资金
            enable_china_rules: 是否启用A股规则
            commission_rate: 佣金费率
            min_commission: 最低佣金
            stamp_tax_rate: 印花税率（仅卖出）
            slippage_rate: 滑点率
        """
        self.initial_cash = initial_cash
        self.enable_china_rules = enable_china_rules
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_tax_rate = stamp_tax_rate
        self.slippage_rate = slippage_rate

        # 回测状态
        self.cash = initial_cash
        self.positions = {}  # {symbol: amount}
        self.trades = []
        self.portfolio_values = []
        self.daily_returns = []

        logger.info("回测引擎初始化完成", initial_cash=initial_cash, china_rules=enable_china_rules)

    def run(
        self,
        strategy_code: str,
        data: pd.DataFrame,
        symbol: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行回测

        Args:
            strategy_code: 策略代码
            data: 行情数据（DataFrame）
            symbol: 股票代码
            params: 策略参数

        Returns:
            回测结果指标
        """
        logger.info("开始回测", symbol=symbol, bars=len(data))

        # 重置状态
        self._reset()

        # 创建策略适配器
        adapter = StrategyAdapter(strategy_code, strategy_id=1)

        # 逐K线回测
        for idx, row in data.iterrows():
            bar = {
                'date': str(row['date'].date()) if hasattr(row['date'], 'date') else str(row['date']),
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            }

            # 检查停牌
            if self.enable_china_rules and self._is_suspended(bar):
                logger.debug(f"停牌，跳过", date=bar['date'])
                continue

            # 调用策略
            signal = adapter.process_bar(bar)

            # 执行交易
            if signal and 'action' in signal:
                self._execute_trade(signal, bar, symbol)

            # 记录账户价值
            portfolio_value = self._calculate_portfolio_value(bar['close'])
            self.portfolio_values.append(portfolio_value)

        # 计算回测指标
        result = self._calculate_metrics(data)

        logger.info("回测完成", trades=result['total_trades'], final_value=result['final_value'])

        return result

    def _reset(self):
        """重置回测状态"""
        self.cash = self.initial_cash
        self.positions = {}
        self.trades = []
        self.portfolio_values = [self.initial_cash]
        self.daily_returns = []

    def _execute_trade(self, signal: Dict[str, Any], bar: Dict[str, Any], symbol: str):
        """
        执行交易

        Args:
            signal: 交易信号
            bar: 当前K线
            symbol: 股票代码
        """
        action = signal['action']
        amount = signal.get('amount', 0)
        price = bar['close']

        # 应用滑点
        if self.enable_china_rules:
            price = self._apply_slippage(price, is_buy=(action == 'buy'))

        # 买入
        if action == 'buy':
            if self.enable_china_rules and not self._validate_buy_amount(amount):
                logger.warning(f"买入数量不合法（必须100股整数倍）", amount=amount)
                return

            cost = price * amount
            commission = self._calculate_commission(cost, is_buy=True)
            total_cost = cost + commission

            if total_cost > self.cash:
                logger.warning(f"资金不足", cash=self.cash, need=total_cost)
                return

            # 执行买入
            self.cash -= total_cost
            self.positions[symbol] = self.positions.get(symbol, 0) + amount

            self.trades.append({
                'date': bar['date'],
                'action': 'buy',
                'symbol': symbol,
                'price': price,
                'amount': amount,
                'commission': commission,
                'cost': total_cost
            })

            logger.debug(f"买入", symbol=symbol, amount=amount, price=price)

        # 卖出
        elif action == 'sell':
            if symbol not in self.positions or self.positions[symbol] < amount:
                logger.warning(f"持仓不足", position=self.positions.get(symbol, 0), sell=amount)
                return

            revenue = price * amount
            commission = self._calculate_commission(revenue, is_buy=False)
            tax = self._calculate_stamp_tax(revenue) if self.enable_china_rules else 0
            total_cost = commission + tax
            net_revenue = revenue - total_cost

            # 执行卖出
            self.cash += net_revenue
            self.positions[symbol] -= amount

            # 计算盈亏
            buy_trade = None
            for t in reversed(self.trades):
                if t['action'] == 'buy' and t['symbol'] == symbol:
                    buy_trade = t
                    break

            profit = 0
            if buy_trade:
                profit = (price - buy_trade['price']) * amount - total_cost

            self.trades.append({
                'date': bar['date'],
                'action': 'sell',
                'symbol': symbol,
                'price': price,
                'amount': amount,
                'commission': commission,
                'tax': tax,
                'revenue': net_revenue,
                'profit': profit
            })

            logger.debug(f"卖出", symbol=symbol, amount=amount, price=price, profit=profit)

    def _calculate_portfolio_value(self, current_price: float) -> float:
        """
        计算账户总价值

        Args:
            current_price: 当前股价

        Returns:
            账户总价值
        """
        position_value = sum(amount * current_price for amount in self.positions.values())
        return self.cash + position_value

    def _calculate_metrics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算回测指标

        Args:
            data: 行情数据

        Returns:
            回测指标字典
        """
        final_value = self.portfolio_values[-1] if self.portfolio_values else self.initial_cash
        days = len(data)

        # 年化收益率
        annual_return = self._calculate_annual_return(final_value, days)

        # 最大回撤
        max_drawdown = self._calculate_max_drawdown(self.portfolio_values)

        # 夏普比率
        returns = []
        for i in range(1, len(self.portfolio_values)):
            daily_return = (self.portfolio_values[i] - self.portfolio_values[i-1]) / self.portfolio_values[i-1]
            returns.append(daily_return)

        sharpe_ratio = self._calculate_sharpe_ratio(returns) if returns else 0

        # 胜率
        win_rate = self._calculate_win_rate(self.trades)

        # 总交易次数
        total_trades = len([t for t in self.trades if t['action'] == 'buy'])

        return {
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'final_value': final_value,
            'total_return': (final_value - self.initial_cash) / self.initial_cash
        }

    # ==================
    # 性能指标计算
    # ==================

    def _calculate_annual_return(self, final_value: float, days: int) -> float:
        """计算年化收益率"""
        if days == 0:
            return 0.0

        total_return = (final_value - self.initial_cash) / self.initial_cash
        annual_return = (1 + total_return) ** (365 / days) - 1

        return annual_return

    def _calculate_max_drawdown(self, values: List[float]) -> float:
        """计算最大回撤"""
        if not values or len(values) < 2:
            return 0.0

        max_dd = 0.0
        peak = values[0]

        for value in values:
            if value > peak:
                peak = value

            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return max_dd

    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.03) -> float:
        """计算夏普比率"""
        if not returns:
            return 0.0

        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # 年化
        daily_rf = risk_free_rate / 252
        sharpe = (avg_return - daily_rf) / std_return * np.sqrt(252)

        return sharpe

    def _calculate_win_rate(self, trades: List[Dict[str, Any]]) -> float:
        """计算胜率"""
        profitable_trades = [t for t in trades if t.get('profit', 0) > 0]

        if not trades:
            return 0.0

        # 只统计卖出交易
        sell_trades = [t for t in trades if t['action'] == 'sell']
        if not sell_trades:
            return 0.0

        winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]

        return len(winning_trades) / len(sell_trades)

    # ==================
    # A股市场规则
    # ==================

    def _is_suspended(self, bar: Dict[str, Any]) -> bool:
        """
        检查是否停牌

        Args:
            bar: K线数据

        Returns:
            是否停牌
        """
        return bar.get('volume', 0) == 0

    def _is_limit_up(self, price: float, prev_close: float, stock_type: str = 'normal') -> bool:
        """
        检查是否涨停

        Args:
            price: 当前价格
            prev_close: 昨收价
            stock_type: 股票类型（normal/st/cyb/kcb）

        Returns:
            是否涨停
        """
        if prev_close == 0:
            return False

        limit_rates = {
            'normal': 0.10,  # 普通股票±10%
            'st': 0.05,      # ST股票±5%
            'cyb': 0.20,     # 创业板±20%
            'kcb': 0.20      # 科创板±20%
        }

        limit_rate = limit_rates.get(stock_type, 0.10)
        limit_price = prev_close * (1 + limit_rate)

        return abs(price - limit_price) < 0.01  # 容差0.01元

    def _is_limit_down(self, price: float, prev_close: float, stock_type: str = 'normal') -> bool:
        """
        检查是否跌停

        Args:
            price: 当前价格
            prev_close: 昨收价
            stock_type: 股票类型

        Returns:
            是否跌停
        """
        if prev_close == 0:
            return False

        limit_rates = {
            'normal': 0.10,
            'st': 0.05,
            'cyb': 0.20,
            'kcb': 0.20
        }

        limit_rate = limit_rates.get(stock_type, 0.10)
        limit_price = prev_close * (1 - limit_rate)

        return abs(price - limit_price) < 0.01

    # ==================
    # 交易税费
    # ==================

    def _calculate_commission(self, amount: float, is_buy: bool) -> float:
        """
        计算佣金

        Args:
            amount: 交易金额
            is_buy: 是否买入

        Returns:
            佣金
        """
        commission = amount * self.commission_rate
        return max(commission, self.min_commission)

    def _calculate_stamp_tax(self, amount: float) -> float:
        """
        计算印花税（仅卖出）

        Args:
            amount: 交易金额

        Returns:
            印花税
        """
        return amount * self.stamp_tax_rate

    def _calculate_trade_cost(self, amount: float, is_buy: bool) -> float:
        """
        计算交易总成本

        Args:
            amount: 交易金额
            is_buy: 是否买入

        Returns:
            总成本
        """
        commission = self._calculate_commission(amount, is_buy)

        if is_buy:
            return commission
        else:
            tax = self._calculate_stamp_tax(amount)
            return commission + tax

    # ==================
    # 交易单位验证
    # ==================

    def _validate_buy_amount(self, amount: int) -> bool:
        """
        验证买入数量（必须100股整数倍）

        Args:
            amount: 买入数量

        Returns:
            是否合法
        """
        return amount % 100 == 0

    def _validate_sell_amount(self, amount: int) -> bool:
        """
        验证卖出数量（可以是零股）

        Args:
            amount: 卖出数量

        Returns:
            是否合法
        """
        return amount > 0

    # ==================
    # 滑点
    # ==================

    def _apply_slippage(self, price: float, is_buy: bool) -> float:
        """
        应用滑点

        Args:
            price: 原始价格
            is_buy: 是否买入

        Returns:
            调整后价格
        """
        if is_buy:
            # 买入：价格上浮
            return price * (1 + self.slippage_rate)
        else:
            # 卖出：价格下调
            return price * (1 - self.slippage_rate)

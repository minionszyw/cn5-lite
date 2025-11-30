"""
CN5-Lite 风控验证器

功能:
1. 总资金止损（10%）
2. 黑名单股票（ST等）
3. 单日亏损限制（5%）
4. 单策略资金占用（30%）
5. 单笔过大（20%）
6. 异常交易频率（20笔/小时）
7. 涨跌停板检测
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from app.logger import get_logger
from app.errors import RiskError

logger = get_logger(__name__)


# ==================
# 7层风控验证器
# ==================

class RiskValidator:
    """
    7层风控验证器

    功能:
    1. 总资金止损
    2. 黑名单股票
    3. 单日亏损限制
    4. 单策略资金占用
    5. 单笔过大
    6. 交易频率限制
    7. 涨跌停板检测
    """

    def __init__(
        self,
        total_capital: float,
        max_total_loss_rate: float = 0.10,      # 总资金止损10%
        max_daily_loss_rate: float = 0.05,      # 单日亏损5%
        max_strategy_capital_rate: float = 0.30, # 单策略30%
        max_single_trade_rate: float = 0.20,    # 单笔20%
        max_trades_per_hour: int = 20,          # 每小时20笔
        blacklist: Optional[List[str]] = None
    ):
        """
        初始化风控验证器

        Args:
            total_capital: 总资金
            max_total_loss_rate: 总资金最大亏损率
            max_daily_loss_rate: 单日最大亏损率
            max_strategy_capital_rate: 单策略最大资金占用率
            max_single_trade_rate: 单笔最大交易占比
            max_trades_per_hour: 每小时最大交易次数
            blacklist: 自定义黑名单
        """
        self.total_capital = total_capital
        self.max_total_loss_rate = max_total_loss_rate
        self.max_daily_loss_rate = max_daily_loss_rate
        self.max_strategy_capital_rate = max_strategy_capital_rate
        self.max_single_trade_rate = max_single_trade_rate
        self.max_trades_per_hour = max_trades_per_hour

        # 状态管理
        self.current_account_value = total_capital
        self.daily_start_value = total_capital
        self.strategy_capitals: Dict[int, float] = {}  # {strategy_id: capital}
        self.prev_close_prices: Dict[str, float] = {}  # {symbol: price}
        self.trade_timestamps: List[datetime] = []

        # 黑名单
        self.blacklist: Set[str] = set(blacklist) if blacklist else set()
        self._init_default_blacklist()

        logger.info("风控验证器初始化完成", total_capital=total_capital)

    def _init_default_blacklist(self):
        """初始化默认黑名单（ST、退市等）"""
        # ST股票特征
        self.st_keywords = ['ST', '*ST', 'S*ST', '退市']

    def validate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行7层风控验证

        Args:
            signal: 交易信号

        Returns:
            {
                "passed": bool,
                "reason": str,
                "risk_score": int  # 0-100
            }
        """
        # 提取信号字段
        action = signal.get('action')
        symbol = signal.get('symbol', '')
        amount = signal.get('amount', 0)
        price = signal.get('price', 0)
        strategy_id = signal.get('strategy_id', 1)

        trade_value = amount * price
        risk_factors = []
        risk_score = 0

        # 第1层：总资金止损
        total_loss_rate = (self.total_capital - self.current_account_value) / self.total_capital
        if total_loss_rate > self.max_total_loss_rate:
            return {
                'passed': False,
                'reason': f'总资金止损触发：当前亏损{total_loss_rate:.1%}，超过限制{self.max_total_loss_rate:.1%}',
                'risk_score': 100
            }

        # 累加风险评分
        if total_loss_rate > self.max_total_loss_rate * 0.5:
            risk_score += 20

        # 第2层：黑名单股票
        if self._is_blacklisted(symbol):
            return {
                'passed': False,
                'reason': f'黑名单股票：{symbol}',
                'risk_score': 100
            }

        # 第3层：单日亏损限制
        daily_loss_rate = (self.daily_start_value - self.current_account_value) / self.daily_start_value
        if daily_loss_rate > self.max_daily_loss_rate:
            return {
                'passed': False,
                'reason': f'单日亏损限制触发：当前亏损{daily_loss_rate:.1%}，超过限制{self.max_daily_loss_rate:.1%}',
                'risk_score': 100
            }

        # 累加风险评分
        if daily_loss_rate > self.max_daily_loss_rate * 0.5:
            risk_score += 15

        # 第4层：单策略资金占用（仅买入）
        if action == 'buy':
            current_capital = self.strategy_capitals.get(strategy_id, 0)
            new_capital = current_capital + trade_value
            capital_rate = new_capital / self.total_capital

            if capital_rate > self.max_strategy_capital_rate:
                return {
                    'passed': False,
                    'reason': f'单策略资金占用超限：当前{capital_rate:.1%}，超过限制{self.max_strategy_capital_rate:.1%}',
                    'risk_score': 100
                }

            # 累加风险评分
            if capital_rate > self.max_strategy_capital_rate * 0.7:
                risk_score += 15

        # 第5层：单笔过大
        trade_rate = trade_value / self.total_capital
        if trade_rate > self.max_single_trade_rate:
            return {
                'passed': False,
                'reason': f'单笔交易过大：当前{trade_rate:.1%}，超过限制{self.max_single_trade_rate:.1%}',
                'risk_score': 100
            }

        # 累加风险评分
        if trade_rate > self.max_single_trade_rate * 0.7:
            risk_score += 20
        elif trade_rate > self.max_single_trade_rate * 0.5:
            risk_score += 10

        # 第6层：交易频率
        recent_trades = self._count_recent_trades(hours=1)
        if recent_trades >= self.max_trades_per_hour:
            return {
                'passed': False,
                'reason': f'交易频率过高：1小时内{recent_trades}笔，超过限制{self.max_trades_per_hour}笔',
                'risk_score': 100
            }

        # 累加风险评分
        if recent_trades > self.max_trades_per_hour * 0.7:
            risk_score += 15

        # 第7层：涨跌停板
        if symbol in self.prev_close_prices:
            prev_close = self.prev_close_prices[symbol]
            limit_result = self._check_limit_price(symbol, price, prev_close, action)

            if not limit_result['allowed']:
                return {
                    'passed': False,
                    'reason': limit_result['reason'],
                    'risk_score': 100
                }

        # 所有层级通过
        logger.info(f"风控验证通过", symbol=symbol, amount=amount, risk_score=risk_score)

        return {
            'passed': True,
            'reason': '通过',
            'risk_score': risk_score
        }

    # ==================
    # 第1层：总资金止损
    # ==================

    def update_account_value(self, value: float):
        """更新账户总价值"""
        self.current_account_value = value

    # ==================
    # 第2层：黑名单
    # ==================

    def _is_blacklisted(self, symbol: str) -> bool:
        """
        检查是否在黑名单中

        Args:
            symbol: 股票代码

        Returns:
            是否在黑名单
        """
        # 检查自定义黑名单
        if symbol in self.blacklist:
            return True

        # 检查ST等特殊股票
        for keyword in self.st_keywords:
            if keyword in symbol:
                return True

        return False

    # ==================
    # 第3层：单日亏损
    # ==================

    def update_daily_start_value(self, value: float):
        """更新今日开始价值"""
        self.daily_start_value = value

    # ==================
    # 第4层：单策略资金占用
    # ==================

    def update_strategy_capital(self, strategy_id: int, capital: float):
        """
        更新策略资金占用

        Args:
            strategy_id: 策略ID
            capital: 占用资金
        """
        self.strategy_capitals[strategy_id] = capital

    # ==================
    # 第5层：单笔过大
    # （在validate中实现）
    # ==================

    # ==================
    # 第6层：交易频率
    # ==================

    def record_trade(self, timestamp: Optional[datetime] = None):
        """
        记录交易时间

        Args:
            timestamp: 交易时间（默认当前时间）
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.trade_timestamps.append(timestamp)

        # 清理1小时以外的记录
        cutoff = datetime.now() - timedelta(hours=1)
        self.trade_timestamps = [t for t in self.trade_timestamps if t > cutoff]

    def _count_recent_trades(self, hours: int = 1) -> int:
        """
        统计最近N小时的交易次数

        Args:
            hours: 小时数

        Returns:
            交易次数
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        return sum(1 for t in self.trade_timestamps if t > cutoff)

    # ==================
    # 第7层：涨跌停板
    # ==================

    def update_prev_close(self, symbol: str, price: float):
        """
        更新昨收价

        Args:
            symbol: 股票代码
            price: 昨收价
        """
        self.prev_close_prices[symbol] = price

    def _check_limit_price(
        self,
        symbol: str,
        current_price: float,
        prev_close: float,
        action: str
    ) -> Dict[str, Any]:
        """
        检查涨跌停板

        Args:
            symbol: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
            action: 交易动作

        Returns:
            {"allowed": bool, "reason": str}
        """
        if prev_close == 0:
            return {'allowed': True, 'reason': ''}

        # 判断股票类型
        stock_type = self._get_stock_type(symbol)

        # 涨跌停幅度
        limit_rates = {
            'normal': 0.10,  # 普通股票±10%
            'st': 0.05,      # ST股票±5%
            'cyb': 0.20,     # 创业板±20%
            'kcb': 0.20      # 科创板±20%
        }

        limit_rate = limit_rates.get(stock_type, 0.10)

        # 计算涨跌幅
        price_change_rate = (current_price - prev_close) / prev_close

        # 检查涨停
        if price_change_rate >= limit_rate - 0.001:  # 容差0.1%
            if action == 'buy':
                return {
                    'allowed': False,
                    'reason': f'涨停板，不建议买入：当前涨幅{price_change_rate:.1%}'
                }

        # 检查跌停
        if price_change_rate <= -limit_rate + 0.001:  # 容差0.1%
            if action == 'sell':
                return {
                    'allowed': False,
                    'reason': f'跌停板，不建议卖出：当前跌幅{price_change_rate:.1%}'
                }

        return {'allowed': True, 'reason': ''}

    def _get_stock_type(self, symbol: str) -> str:
        """
        获取股票类型

        Args:
            symbol: 股票代码

        Returns:
            股票类型（normal/st/cyb/kcb）
        """
        # ST股票
        if any(kw in symbol for kw in self.st_keywords):
            return 'st'

        # 科创板（688开头）
        if symbol.startswith('SH688'):
            return 'kcb'

        # 创业板（300开头）
        if symbol.startswith('SZ300'):
            return 'cyb'

        # 普通股票
        return 'normal'

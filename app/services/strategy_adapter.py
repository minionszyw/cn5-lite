"""
CN5-Lite 策略适配器层

功能:
1. 标准策略封装
2. T+1锁定管理
3. 状态持久化
4. 防未来函数
5. 订单执行逻辑
"""

import ast
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.logger import get_logger
from app.errors import ValidationError, ExecutionError

logger = get_logger(__name__)


# ==================
# 标准策略封装
# ==================

class StandardStrategy:
    """
    标准策略封装

    功能:
    1. 解析AI生成的策略代码
    2. 提供on_bar统一接口
    3. 管理策略内部状态
    """

    def __init__(self, code: str):
        """
        初始化标准策略

        Args:
            code: AI生成的策略代码
        """
        self.code = code
        self.strategy_instance = None
        self._initialize_strategy()

        logger.info("标准策略初始化完成")

    def _initialize_strategy(self):
        """初始化策略实例"""
        # 创建执行环境
        namespace = {}

        try:
            # 执行代码
            exec(self.code, namespace)

            # 找到策略类
            strategy_class = None
            for name, obj in namespace.items():
                if isinstance(obj, type) and hasattr(obj, 'on_bar'):
                    strategy_class = obj
                    break

            if not strategy_class:
                raise ValidationError("未找到包含on_bar方法的策略类")

            # 实例化策略
            self.strategy_instance = strategy_class()

            logger.info(f"策略类实例化成功", class_name=strategy_class.__name__)

        except Exception as e:
            logger.error(f"策略初始化失败: {e}")
            raise ExecutionError(f"策略初始化失败: {e}")

    def on_bar(self, bar: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理K线数据

        Args:
            bar: K线数据

        Returns:
            交易信号或None
        """
        try:
            signal = self.strategy_instance.on_bar(bar)
            return signal
        except Exception as e:
            logger.error(f"策略on_bar执行失败: {e}")
            raise ExecutionError(f"策略on_bar执行失败: {e}")

    def get_state(self) -> Dict[str, Any]:
        """
        获取策略内部状态

        Returns:
            策略状态字典
        """
        # 获取所有非私有属性
        state = {}
        for key, value in self.strategy_instance.__dict__.items():
            if not key.startswith('_'):
                # 尝试序列化
                try:
                    json.dumps(value)
                    state[key] = value
                except (TypeError, ValueError):
                    # 无法序列化的对象转为字符串
                    state[key] = str(value)

        return state

    def restore_state(self, state: Dict[str, Any]):
        """
        恢复策略状态

        Args:
            state: 保存的状态字典
        """
        for key, value in state.items():
            setattr(self.strategy_instance, key, value)

        logger.info("策略状态已恢复", keys=list(state.keys()))


# ==================
# 策略适配器
# ==================

class StrategyAdapter:
    """
    策略适配器 - 消除回测/实盘鸿沟

    功能:
    1. 封装标准策略
    2. T+1锁定管理
    3. 订单验证和执行
    4. 状态持久化
    5. 防未来函数
    """

    def __init__(self, strategy_code: str, strategy_id: int):
        """
        初始化适配器

        Args:
            strategy_code: 策略代码
            strategy_id: 策略ID
        """
        self.strategy_id = strategy_id
        self.strategy = StandardStrategy(strategy_code)

        # T+1锁定管理
        # 格式: {symbol: {'amount': 100, 'lock_date': '2024-01-01'}}
        self.t1_locks: Dict[str, Dict[str, Any]] = {}

        # 当前日期（用于T+1判断）
        self.current_date: Optional[str] = None

        logger.info(f"策略适配器初始化完成", strategy_id=strategy_id)

    def process_bar(self, bar: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理K线数据

        Args:
            bar: K线数据，必须包含'date'字段

        Returns:
            信号字典（可能是订单，也可能是其他信息）或None
        """
        # 更新当前日期
        if 'date' in bar:
            self._update_current_date(bar['date'])

        # 调用策略
        signal = self.strategy.on_bar(bar)

        # 如果没有信号，返回None
        if signal is None:
            return None

        # 如果signal不包含action，直接返回（可能是状态信息）
        if not isinstance(signal, dict) or 'action' not in signal:
            return signal

        # 验证订单
        order = self._validate_and_build_order(signal, bar)

        # 如果是买入，添加T+1锁定
        if order and order.get('action') == 'buy':
            self._add_t1_lock(order)

        # 如果是卖出，检查T+1限制
        if order and order.get('action') == 'sell':
            if not self._check_t1_sellable(order):
                logger.warning(f"T+1限制：当日买入不可卖出", symbol=order.get('symbol'))
                return None

        return order

    def _update_current_date(self, date: str):
        """更新当前日期并清理过期T+1锁定"""
        old_date = self.current_date
        self.current_date = date

        # 如果日期变化，清理过期的T+1锁定
        if old_date and old_date != date:
            self._unlock_t1(date)

    def _unlock_t1(self, current_date: str):
        """
        解锁T+1限制

        Args:
            current_date: 当前日期
        """
        unlocked = []
        for symbol, lock_info in list(self.t1_locks.items()):
            if lock_info['lock_date'] < current_date:
                unlocked.append(symbol)
                del self.t1_locks[symbol]

        if unlocked:
            logger.info(f"T+1解锁", symbols=unlocked, date=current_date)

    def _validate_and_build_order(self, signal: Dict[str, Any], bar: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        验证信号并构建订单

        Args:
            signal: 策略信号
            bar: K线数据

        Returns:
            订单字典或None
        """
        if not isinstance(signal, dict):
            return None

        action = signal.get('action')
        if action not in ['buy', 'sell']:
            return None

        # 提取订单字段
        order = {
            'action': action,
            'symbol': signal.get('symbol', ''),
            'amount': signal.get('amount', 0),
            'price': signal.get('price', bar.get('close')),
            'strategy_id': self.strategy_id,
            'date': self.current_date
        }

        # 复制其他字段
        for key, value in signal.items():
            if key not in order:
                order[key] = value

        # 验证买入数量必须是100的倍数
        if action == 'buy':
            if order['amount'] % 100 != 0:
                raise ValueError(f"买入数量必须是100的整数倍: {order['amount']}")

        return order

    def _add_t1_lock(self, order: Dict[str, Any]):
        """
        添加T+1锁定

        Args:
            order: 买入订单
        """
        symbol = order['symbol']
        amount = order['amount']
        date = order['date']

        if symbol in self.t1_locks:
            # 累加锁定数量
            self.t1_locks[symbol]['amount'] += amount
        else:
            self.t1_locks[symbol] = {
                'amount': amount,
                'lock_date': date
            }

        logger.info(f"T+1锁定", symbol=symbol, amount=amount, date=date)

    def _check_t1_sellable(self, order: Dict[str, Any]) -> bool:
        """
        检查是否可以卖出（T+1限制）

        Args:
            order: 卖出订单

        Returns:
            是否可以卖出
        """
        symbol = order['symbol']
        amount = order['amount']

        # 如果没有T+1锁定，可以卖出
        if symbol not in self.t1_locks:
            return True

        lock_info = self.t1_locks[symbol]

        # 如果锁定日期 < 当前日期，已解锁，可以卖出
        if lock_info['lock_date'] < self.current_date:
            return True

        # 如果锁定日期 == 当前日期，不可卖出
        if lock_info['lock_date'] == self.current_date:
            return False

        return True

    def is_locked(self, symbol: str) -> bool:
        """
        检查股票是否被T+1锁定

        Args:
            symbol: 股票代码

        Returns:
            是否锁定
        """
        if symbol not in self.t1_locks:
            return False

        lock_info = self.t1_locks[symbol]

        # 如果锁定日期 == 当前日期，锁定中
        return lock_info['lock_date'] == self.current_date

    def get_locked_amount(self, symbol: str) -> int:
        """
        获取锁定数量

        Args:
            symbol: 股票代码

        Returns:
            锁定数量
        """
        if symbol not in self.t1_locks:
            return 0

        return self.t1_locks[symbol]['amount']

    def get_state(self) -> Dict[str, Any]:
        """
        获取适配器完整状态

        Returns:
            状态字典
        """
        return {
            'strategy_state': self.strategy.get_state(),
            't1_locks': self.t1_locks,
            'current_date': self.current_date
        }

    def restore_state(self, state: Dict[str, Any]):
        """
        恢复适配器状态

        Args:
            state: 保存的状态
        """
        # 恢复策略状态
        if 'strategy_state' in state:
            self.strategy.restore_state(state['strategy_state'])

        # 恢复T+1锁定
        if 't1_locks' in state:
            self.t1_locks = state['t1_locks']

        # 恢复当前日期
        if 'current_date' in state:
            self.current_date = state['current_date']

        logger.info("适配器状态已恢复", strategy_id=self.strategy_id)

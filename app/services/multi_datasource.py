"""
多数据源管理器
功能：
1. 数据源容错（AkShare → Baostock → Efinance）
2. 数据归一化（统一列名、类型、排序）
3. OHLC合法性校验
4. 停牌检测和处理
5. 异常值过滤（3-sigma）
6. Redis限流器（令牌桶算法）
"""

import pandas as pd
import numpy as np
import redis
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from datetime import datetime
import logging

from app.errors import DataSourceError, DataValidationError, CN5Error

# 配置日志
logger = logging.getLogger(__name__)


# ==================
# 数据源提供者基类
# ==================

class BaseDataProvider(ABC):
    """数据源基类"""

    @abstractmethod
    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取K线数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            K线数据DataFrame
        """
        pass


# ==================
# 具体数据源实现
# ==================

class AkShareProvider(BaseDataProvider):
    """AkShare数据源"""

    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取AkShare数据"""
        try:
            import akshare as ak

            # 转换股票代码格式（去除.SZ/.SH后缀）
            symbol_ak = symbol.replace('.SZ', '').replace('.SH', '')

            # 转换日期格式（YYYY-MM-DD → YYYYMMDD）
            start_date_ak = start_date.replace('-', '')
            end_date_ak = end_date.replace('-', '')

            # 获取数据（前复权）
            data = ak.stock_zh_a_hist(
                symbol=symbol_ak,
                start_date=start_date_ak,
                end_date=end_date_ak,
                adjust="qfq"  # 前复权
            )

            return data

        except Exception as e:
            logger.error(f"AkShare获取数据失败: {e}")
            raise DataSourceError(f"AkShare失败: {e}")


class BaoStockProvider(BaseDataProvider):
    """Baostock数据源"""

    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取Baostock数据"""
        try:
            import baostock as bs

            # 登录
            bs.login()

            try:
                # 查询历史K线数据
                rs = bs.query_history_k_data_plus(
                    symbol,
                    "date,open,high,low,close,volume",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",  # 日线
                    adjustflag="2"  # 前复权
                )

                # 转换为DataFrame
                data = rs.get_data()

                return data

            finally:
                # 登出
                bs.logout()

        except Exception as e:
            logger.error(f"Baostock获取数据失败: {e}")
            raise DataSourceError(f"Baostock失败: {e}")


class EfinanceProvider(BaseDataProvider):
    """Efinance数据源"""

    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取Efinance数据"""
        try:
            import efinance as ef

            # 获取数据
            data = ef.stock.get_quote_history(
                symbol,
                beg=start_date,
                end=end_date,
                klt=101,  # 日K
                fqt=1  # 前复权
            )

            return data

        except Exception as e:
            logger.error(f"Efinance获取数据失败: {e}")
            raise DataSourceError(f"Efinance失败: {e}")


# ==================
# 数据归一化器
# ==================

class DataNormalizer:
    """
    数据归一化器
    功能：
    1. 统一列名
    2. 统一数据类型
    3. 排序
    4. OHLC合法性校验
    5. 停牌处理
    6. 异常值过滤
    """

    # 列名映射
    COLUMN_MAPPING = {
        'akshare': {
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        },
        'baostock': {
            'date': 'date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        },
        'efinance': {
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        }
    }

    def normalize(self, data: pd.DataFrame, source: str) -> pd.DataFrame:
        """
        归一化数据

        Args:
            data: 原始数据
            source: 数据源名称 (akshare/baostock/efinance)

        Returns:
            归一化后的数据
        """
        if data.empty:
            return data

        # 1. 重命名列
        mapping = self.COLUMN_MAPPING.get(source, {})
        data = data.rename(columns=mapping)

        # 2. 只保留标准列
        standard_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        data = data[[col for col in standard_columns if col in data.columns]]

        # 3. 转换数据类型
        data['date'] = pd.to_datetime(data['date'])

        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                data[col] = data[col].astype(float)

        if 'volume' in data.columns:
            data['volume'] = data['volume'].astype(int)

        # 4. 排序
        data = data.sort_values('date').reset_index(drop=True)

        return data

    def validate_ohlc(self, data: pd.DataFrame) -> None:
        """
        OHLC合法性校验

        规则：
        - high >= max(open, close, low)
        - low <= min(open, close, high)

        Args:
            data: K线数据

        Raises:
            DataValidationError: OHLC数据非法
        """
        if data.empty:
            return

        # 检查 high >= max(open, close, low)
        max_price = data[['open', 'close', 'low']].max(axis=1)
        invalid_high = data[data['high'] < max_price]

        if len(invalid_high) > 0:
            raise DataValidationError(f"OHLC数据非法: {len(invalid_high)}条high < max(open,close,low)")

        # 检查 low <= min(open, close, high)
        min_price = data[['open', 'close', 'high']].min(axis=1)
        invalid_low = data[data['low'] > min_price]

        if len(invalid_low) > 0:
            raise DataValidationError(f"OHLC数据非法: {len(invalid_low)}条low > min(open,close,high)")

    def is_halt(self, bar: pd.Series) -> bool:
        """
        停牌检测

        Args:
            bar: 单根K线数据

        Returns:
            是否停牌
        """
        return bar['volume'] == 0

    def fill_halt_days(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        停牌日处理

        策略：
        - volume保持0
        - 价格用前一日收盘价填充

        Args:
            data: K线数据

        Returns:
            处理后的数据
        """
        if data.empty:
            return data

        data = data.copy()

        # 停牌标记: volume=0
        halt_mask = data['volume'] == 0

        # 价格用前一日填充
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                data.loc[halt_mask, col] = data[col].ffill()

        return data

    def remove_outliers(self, data: pd.DataFrame, n_sigma: float = 3.0) -> pd.DataFrame:
        """
        3-sigma异常值过滤

        Args:
            data: K线数据
            n_sigma: sigma倍数

        Returns:
            过滤后的数据
        """
        if data.empty:
            return data

        data = data.copy()

        # 对每个价格列应用3-sigma过滤
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                mean = data[col].mean()
                std = data[col].std()

                lower = mean - n_sigma * std
                upper = mean + n_sigma * std

                # 过滤异常值
                data = data[(data[col] >= lower) & (data[col] <= upper)]

        return data


# ==================
# Redis限流器
# ==================

class RateLimiter:
    """
    Redis令牌桶限流器

    功能：
    - 防止API频繁调用被封IP
    - 每个数据源独立限流
    - 使用Redis存储计数
    """

    def __init__(self, redis_client: redis.Redis, limit: int = 1, window: int = 1):
        """
        初始化限流器

        Args:
            redis_client: Redis客户端
            limit: 限流次数
            window: 时间窗口（秒）
        """
        self.redis = redis_client
        self.limit = limit
        self.window = window

    def check(self, source_name: str) -> bool:
        """
        检查是否允许请求

        Args:
            source_name: 数据源名称

        Returns:
            是否允许请求
        """
        key = f"rate_limit:{source_name}"

        # 令牌桶算法
        current = self.redis.incr(key)

        if current == 1:
            # 第一次请求，设置过期时间
            self.redis.expire(key, self.window)

        # 判断是否超过限制
        return current <= self.limit


# ==================
# 多数据源管理器
# ==================

class DataSourceManager:
    """
    多数据源管理器

    功能：
    1. 多源容错（AkShare → Baostock → Efinance）
    2. 数据归一化
    3. 数据缓存（Redis）
    4. 限流保护
    """

    def __init__(self, cache: Optional[redis.Redis] = None):
        """
        初始化管理器

        Args:
            cache: Redis缓存客户端（可选）
        """
        # 配置数据源（按优先级）
        self.sources = [
            {'name': 'akshare', 'priority': 1, 'provider': AkShareProvider()},
            {'name': 'baostock', 'priority': 2, 'provider': BaoStockProvider()},
            {'name': 'efinance', 'priority': 3, 'provider': EfinanceProvider()},
        ]

        # 归一化器
        self.normalizer = DataNormalizer()

        # 缓存
        self.cache = cache

        # 限流器
        self.limiter = RateLimiter(cache, limit=1, window=1) if cache else None

    def fetch_with_fallback(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        多源容错获取数据

        流程：
        1. 检查缓存
        2. 依次尝试各数据源
        3. 限流检查
        4. 数据归一化
        5. 验证和处理
        6. 写入缓存

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            归一化后的K线数据

        Raises:
            DataSourceError: 所有数据源均失败
        """
        # 1. 检查缓存
        if self.cache:
            cache_key = f"kline:{symbol}:{start_date}:{end_date}"
            cached = self.cache.get(cache_key)

            if cached:
                logger.info(f"缓存命中: {cache_key}")
                return pd.read_json(cached)

        # 2. 依次尝试数据源
        last_error = None

        for source in self.sources:
            try:
                # 限流检查
                if self.limiter and not self.limiter.check(source['name']):
                    logger.warning(f"{source['name']} 触发限流，跳过")
                    continue

                logger.info(f"尝试使用 {source['name']} 获取数据...")

                # 获取数据
                data = source['provider'].fetch(symbol, start_date, end_date)

                # 归一化
                data = self.normalizer.normalize(data, source['name'])

                # 验证
                self.normalizer.validate_ohlc(data)

                # 停牌处理
                data = self.normalizer.fill_halt_days(data)

                # 异常值过滤
                data = self.normalizer.remove_outliers(data)

                logger.info(f"{source['name']} 获取数据成功: {len(data)}条")

                # 写入缓存
                if self.cache:
                    self.cache.setex(cache_key, 86400 * 7, data.to_json())  # 缓存7天

                return data

            except Exception as e:
                logger.error(f"{source['name']} 失败: {e}")
                last_error = e
                continue

        # 所有数据源均失败
        raise DataSourceError(f"所有数据源均失败，最后一个错误: {last_error}")

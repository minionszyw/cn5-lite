"""
多数据源管理器单元测试
测试内容：
1. 数据源容错（AkShare → Baostock → Efinance降级）
2. 数据归一化（统一列名、数据类型、排序）
3. OHLC合法性校验
4. 停牌检测和处理
5. 异常值过滤（3-sigma）
6. Redis限流器（令牌桶算法）
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


# ==================
# 数据源管理器测试
# ==================

class TestDataSourceManager:
    """多数据源管理器单元测试"""

    def test_init_with_default_sources(self):
        """测试初始化默认数据源"""
        from app.services.multi_datasource import DataSourceManager

        manager = DataSourceManager()

        assert len(manager.sources) == 3
        assert manager.sources[0]['name'] == 'akshare'
        assert manager.sources[1]['name'] == 'baostock'
        assert manager.sources[2]['name'] == 'efinance'

    def test_fetch_with_fallback_success_first_source(self, mock_akshare_success):
        """测试第一数据源成功获取"""
        from app.services.multi_datasource import DataSourceManager

        manager = DataSourceManager()
        data = manager.fetch_with_fallback('000001.SZ', '2024-01-01', '2024-01-10')

        assert data is not None
        assert len(data) > 0
        # 验证归一化后的列名
        assert list(data.columns) == ['date', 'open', 'high', 'low', 'close', 'volume']
        # 验证数据类型
        assert data['date'].dtype == 'datetime64[ns]'
        assert data['open'].dtype == 'float64'
        assert data['volume'].dtype == 'int64'

    def test_fetch_with_fallback_second_source(self, mock_akshare_fail):
        """测试第一源失败，降级到第二源"""
        from app.services.multi_datasource import DataSourceManager

        # Mock Baostock成功
        with patch('baostock.query_history_k_data_plus') as mock_bs:
            mock_result = Mock()
            mock_result.get_data.return_value = pd.DataFrame({
                'date': ['2024-01-01', '2024-01-02'],
                'open': [10.0, 10.1],
                'high': [10.5, 10.6],
                'low': [9.5, 9.6],
                'close': [10.2, 10.3],
                'volume': [1000000, 1100000]
            })
            mock_bs.return_value = mock_result

            manager = DataSourceManager()
            data = manager.fetch_with_fallback('000001.SZ', '2024-01-01', '2024-01-02')

            assert data is not None
            assert len(data) == 2
            # 验证AkShare被调用过且失败
            assert mock_akshare_fail.called

    def test_fetch_all_sources_fail(self, mock_all_datasources_fail):
        """测试所有数据源均失败"""
        from app.services.multi_datasource import DataSourceManager, DataSourceError

        manager = DataSourceManager()

        with pytest.raises(DataSourceError, match="所有数据源均失败"):
            manager.fetch_with_fallback('000001.SZ', '2024-01-01', '2024-01-10')

    def test_fetch_with_cache_hit(self, redis_client, mock_akshare_success):
        """测试缓存命中"""
        from app.services.multi_datasource import DataSourceManager
        import time

        manager = DataSourceManager(cache=redis_client)

        # 第一次请求（缓存未命中）
        start = time.time()
        data1 = manager.fetch_with_fallback('000001.SZ', '2024-01-01', '2024-01-10')
        first_request_time = time.time() - start

        # 第二次请求（缓存命中）
        start = time.time()
        data2 = manager.fetch_with_fallback('000001.SZ', '2024-01-01', '2024-01-10')
        cache_request_time = time.time() - start

        # 缓存命中应该更快
        assert cache_request_time < first_request_time
        # 数据应该一致
        pd.testing.assert_frame_equal(data1, data2)


# ==================
# 数据归一化测试
# ==================

class TestDataNormalizer:
    """数据归一化器测试"""

    def test_normalize_akshare_data(self):
        """测试AkShare数据归一化"""
        from app.services.multi_datasource import DataNormalizer

        normalizer = DataNormalizer()

        # AkShare原始格式
        raw_data = pd.DataFrame({
            '日期': ['2024-01-01', '2024-01-02'],
            '开盘': [10.0, 10.1],
            '最高': [10.5, 10.6],
            '最低': [9.5, 9.6],
            '收盘': [10.2, 10.3],
            '成交量': [1000000, 1100000]
        })

        normalized = normalizer.normalize(raw_data, source='akshare')

        # 验证列名
        assert list(normalized.columns) == ['date', 'open', 'high', 'low', 'close', 'volume']
        # 验证数据类型
        assert normalized['date'].dtype == 'datetime64[ns]'
        assert normalized['open'].dtype == 'float64'
        assert normalized['volume'].dtype == 'int64'
        # 验证排序
        assert normalized['date'].is_monotonic_increasing

    def test_normalize_baostock_data(self):
        """测试Baostock数据归一化"""
        from app.services.multi_datasource import DataNormalizer

        normalizer = DataNormalizer()

        # Baostock原始格式（已经是标准列名）
        raw_data = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02'],
            'open': ['10.0', '10.1'],  # 注意Baostock返回字符串
            'high': ['10.5', '10.6'],
            'low': ['9.5', '9.6'],
            'close': ['10.2', '10.3'],
            'volume': ['1000000', '1100000']
        })

        normalized = normalizer.normalize(raw_data, source='baostock')

        # 验证数据类型转换
        assert normalized['open'].dtype == 'float64'
        assert normalized['volume'].dtype == 'int64'

    def test_validate_ohlc_success(self):
        """测试OHLC合法性校验 - 合法数据"""
        from app.services.multi_datasource import DataNormalizer

        normalizer = DataNormalizer()

        valid_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=3),
            'open': [10.0, 10.1, 10.2],
            'high': [10.5, 10.6, 10.7],  # high >= max(open, close, low)
            'low': [9.5, 9.6, 9.7],      # low <= min(open, close, high)
            'close': [10.2, 10.3, 10.4],
            'volume': [1000000, 1100000, 1200000]
        })

        # 不应抛出异常
        normalizer.validate_ohlc(valid_data)

    def test_validate_ohlc_invalid_high(self, sample_kline_data_with_invalid_ohlc):
        """测试OHLC合法性校验 - high < close非法"""
        from app.services.multi_datasource import DataNormalizer, DataValidationError

        normalizer = DataNormalizer()

        with pytest.raises(DataValidationError, match="OHLC数据非法"):
            normalizer.validate_ohlc(sample_kline_data_with_invalid_ohlc)

    def test_validate_ohlc_invalid_low(self):
        """测试OHLC合法性校验 - low > open非法"""
        from app.services.multi_datasource import DataNormalizer, DataValidationError

        normalizer = DataNormalizer()

        invalid_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=2),
            'open': [10.0, 10.1],
            'high': [10.5, 10.6],
            'low': [10.8, 10.9],  # low > open, 非法
            'close': [10.2, 10.3],
            'volume': [1000000, 1100000]
        })

        with pytest.raises(DataValidationError):
            normalizer.validate_ohlc(invalid_data)

    def test_fill_halt_days(self, sample_kline_data_with_halt):
        """测试停牌日处理"""
        from app.services.multi_datasource import DataNormalizer

        normalizer = DataNormalizer()

        filled = normalizer.fill_halt_days(sample_kline_data_with_halt)

        # 停牌日volume保持0
        assert filled.loc[4, 'volume'] == 0
        # 停牌日价格用前一日收盘价填充
        assert filled.loc[4, 'close'] == filled.loc[3, 'close']
        assert filled.loc[4, 'open'] == filled.loc[3, 'close']

    def test_remove_outliers_3sigma(self):
        """测试3-sigma异常值过滤"""
        from app.services.multi_datasource import DataNormalizer

        normalizer = DataNormalizer()

        # 创建包含异常值的数据
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'open': [10.0] * 8 + [1000.0, 10.0],  # 第9行是异常值
            'high': [10.5] * 10,
            'low': [9.5] * 10,
            'close': [10.2] * 10,
            'volume': [1000000] * 10
        })

        filtered = normalizer.remove_outliers(data, n_sigma=3.0)

        # 异常值应被移除
        assert len(filtered) < len(data)
        # 正常值应保留
        assert filtered['open'].max() < 100

    def test_is_halt_detection(self):
        """测试停牌检测"""
        from app.services.multi_datasource import DataNormalizer

        normalizer = DataNormalizer()

        # 正常交易日
        normal_bar = pd.Series({'volume': 1000000})
        assert normalizer.is_halt(normal_bar) == False

        # 停牌日（volume=0）
        halt_bar = pd.Series({'volume': 0})
        assert normalizer.is_halt(halt_bar) == True


# ==================
# 限流器测试
# ==================

class TestRateLimiter:
    """Redis限流器测试（令牌桶算法）"""

    def test_rate_limit_allow_first_request(self, redis_client):
        """测试第一次请求允许通过"""
        from app.services.multi_datasource import RateLimiter

        limiter = RateLimiter(redis_client, limit=1, window=1)

        assert limiter.check('akshare') == True

    def test_rate_limit_exceed(self, redis_client):
        """测试限流拒绝超频请求"""
        from app.services.multi_datasource import RateLimiter

        limiter = RateLimiter(redis_client, limit=1, window=1)

        # 第一次请求
        assert limiter.check('akshare') == True
        # 第二次请求应被拒绝（超过1次/秒限制）
        assert limiter.check('akshare') == False

    def test_rate_limit_reset_after_window(self, redis_client):
        """测试限流窗口重置"""
        from app.services.multi_datasource import RateLimiter
        import time

        limiter = RateLimiter(redis_client, limit=1, window=1)

        # 第一次请求
        limiter.check('akshare')

        # 等待超过窗口期
        time.sleep(1.1)

        # 窗口重置后应允许请求
        assert limiter.check('akshare') == True

    def test_rate_limit_per_source(self, redis_client):
        """测试每个数据源独立限流"""
        from app.services.multi_datasource import RateLimiter

        limiter = RateLimiter(redis_client, limit=1, window=1)

        # AkShare第一次请求
        assert limiter.check('akshare') == True
        # AkShare第二次请求被拒绝
        assert limiter.check('akshare') == False

        # Baostock第一次请求应允许（独立限流）
        assert limiter.check('baostock') == True


# ==================
# 数据源提供者测试
# ==================

class TestAkShareProvider:
    """AkShare数据源提供者测试"""

    @pytest.mark.skip(reason="需要实现AkShareProvider类")
    def test_fetch_stock_data(self):
        """测试获取股票数据"""
        from app.services.multi_datasource import AkShareProvider

        provider = AkShareProvider()

        with patch('akshare.stock_zh_a_hist') as mock_ak:
            mock_ak.return_value = pd.DataFrame({
                '日期': ['20240101'],
                '开盘': [10.0],
                '最高': [10.5],
                '最低': [9.5],
                '收盘': [10.2],
                '成交量': [1000000]
            })

            data = provider.fetch('000001.SZ', '2024-01-01', '2024-01-01')

            # 验证调用参数
            mock_ak.assert_called_once()
            args, kwargs = mock_ak.call_args
            assert kwargs.get('adjust') == 'qfq'  # 前复权


class TestBaoStockProvider:
    """Baostock数据源提供者测试"""

    @pytest.mark.skip(reason="需要实现BaoStockProvider类")
    def test_fetch_stock_data(self):
        """测试获取股票数据"""
        from app.services.multi_datasource import BaoStockProvider

        provider = BaoStockProvider()

        with patch('baostock.login'), \
             patch('baostock.logout'), \
             patch('baostock.query_history_k_data_plus') as mock_bs:

            mock_result = Mock()
            mock_result.get_data.return_value = pd.DataFrame({
                'date': ['2024-01-01'],
                'open': ['10.0'],
                'high': ['10.5'],
                'low': ['9.5'],
                'close': ['10.2'],
                'volume': ['1000000']
            })
            mock_bs.return_value = mock_result

            data = provider.fetch('000001.SZ', '2024-01-01', '2024-01-01')

            # 验证调用参数
            mock_bs.assert_called_once()
            args, kwargs = mock_bs.call_args
            assert kwargs.get('adjustflag') == '2'  # 前复权


# ==================
# 错误处理测试
# ==================

class TestErrorHandling:
    """错误处理测试"""

    def test_data_source_error_inheritance(self):
        """测试DataSourceError继承体系"""
        from app.services.multi_datasource import DataSourceError, CN5Error

        # DataSourceError应继承自CN5Error
        assert issubclass(DataSourceError, CN5Error)

    def test_data_validation_error_inheritance(self):
        """测试DataValidationError继承体系"""
        from app.services.multi_datasource import DataValidationError, CN5Error

        # DataValidationError应继承自CN5Error
        assert issubclass(DataValidationError, CN5Error)


# ==================
# 边界条件测试
# ==================

class TestEdgeCases:
    """边界条件测试"""

    def test_empty_data_handling(self):
        """测试空数据处理"""
        from app.services.multi_datasource import DataNormalizer

        normalizer = DataNormalizer()

        empty_data = pd.DataFrame()

        # 应该能够处理空数据而不崩溃
        result = normalizer.fill_halt_days(empty_data)
        assert len(result) == 0

    def test_single_row_data(self):
        """测试单行数据"""
        from app.services.multi_datasource import DataNormalizer

        normalizer = DataNormalizer()

        single_row = pd.DataFrame({
            'date': ['2024-01-01'],
            'open': [10.0],
            'high': [10.5],
            'low': [9.5],
            'close': [10.2],
            'volume': [1000000]
        })

        # 归一化应该正常工作
        result = normalizer.normalize(single_row, source='baostock')
        assert len(result) == 1
        assert list(result.columns) == ['date', 'open', 'high', 'low', 'close', 'volume']

    def test_weekend_and_holidays(self):
        """测试节假日数据"""
        # TODO: 实现节假日处理逻辑后添加测试
        pass


# ==================
# 性能测试
# ==================

class TestPerformance:
    """性能测试"""

    @pytest.mark.slow
    def test_cache_performance_improvement(self, redis_client, mock_akshare_success):
        """测试缓存性能提升"""
        from app.services.multi_datasource import DataSourceManager
        import time

        manager = DataSourceManager(cache=redis_client)

        # 第一次请求（无缓存）
        start = time.time()
        manager.fetch_with_fallback('000001.SZ', '2024-01-01', '2024-01-10')
        no_cache_time = time.time() - start

        # 第二次请求（有缓存）
        start = time.time()
        manager.fetch_with_fallback('000001.SZ', '2024-01-01', '2024-01-10')
        cache_time = time.time() - start

        # 缓存命中应该快至少10倍
        assert cache_time < no_cache_time * 0.1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=app/services/multi_datasource'])

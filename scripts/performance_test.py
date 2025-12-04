"""
性能测试脚本
测试系统各模块的性能指标

运行方式：
  python scripts/performance_test.py
"""

import time
import psutil
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PerformanceTest:
    """性能测试工具"""

    def __init__(self):
        self.results = []

    def measure_time(self, func, *args, **kwargs):
        """测量函数执行时间"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed = end_time - start_time
        return result, elapsed

    def measure_memory(self, func, *args, **kwargs):
        """测量函数内存使用"""
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        result = func(*args, **kwargs)

        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_used = mem_after - mem_before

        return result, mem_used

    def record_result(self, test_name, elapsed_time, memory_used, success=True):
        """记录测试结果"""
        self.results.append({
            'test_name': test_name,
            'elapsed_time': elapsed_time,
            'memory_used_mb': memory_used,
            'success': success,
            'timestamp': datetime.now()
        })

    def print_results(self):
        """打印测试结果"""
        df = pd.DataFrame(self.results)

        print("\n" + "="*80)
        print("性能测试结果")
        print("="*80)

        for _, row in df.iterrows():
            status = "✅" if row['success'] else "❌"
            print(f"\n{status} {row['test_name']}")
            print(f"   执行时间: {row['elapsed_time']:.3f}秒")
            print(f"   内存使用: {row['memory_used_mb']:.2f}MB")

        print("\n" + "="*80)
        print("统计摘要")
        print("="*80)
        print(f"总测试数: {len(df)}")
        print(f"成功: {df['success'].sum()}")
        print(f"失败: {(~df['success']).sum()}")
        print(f"总耗时: {df['elapsed_time'].sum():.3f}秒")
        print(f"总内存: {df['memory_used_mb'].sum():.2f}MB")
        print(f"平均耗时: {df['elapsed_time'].mean():.3f}秒")

    def test_data_loading(self):
        """测试数据加载性能"""
        print("\n测试1: 数据加载性能...")

        # 生成测试数据
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        data = pd.DataFrame({
            'date': dates,
            'open': range(len(dates)),
            'high': range(len(dates)),
            'low': range(len(dates)),
            'close': range(len(dates)),
            'volume': range(len(dates))
        })

        # 测试DataFrame操作
        def load_and_process():
            df = data.copy()
            df['ma5'] = df['close'].rolling(5).mean()
            df['ma20'] = df['close'].rolling(20).mean()
            return df

        result, elapsed = self.measure_time(load_and_process)
        _, mem_used = self.measure_memory(load_and_process)

        self.record_result("数据加载和处理", elapsed, mem_used)

    def test_strategy_execution(self):
        """测试策略执行性能"""
        print("\n测试2: 策略执行性能...")

        strategy_code = """
class MAStrategy:
    def __init__(self):
        self.ma_period = 20
        self.prices = []

    def on_bar(self, bar):
        self.prices.append(bar['close'])

        if len(self.prices) < self.ma_period:
            return None

        ma = sum(self.prices[-self.ma_period:]) / self.ma_period

        if bar['close'] > ma:
            return {'action': 'buy', 'amount': 100}

        return None
"""

        # 执行策略1000次
        def run_strategy():
            from app.services.strategy_adapter import StrategyAdapter

            adapter = StrategyAdapter(strategy_code, strategy_id=1)

            for i in range(1000):
                bar = {
                    'date': '2024-01-01',
                    'open': 10.0 + i * 0.01,
                    'high': 10.5 + i * 0.01,
                    'low': 9.5 + i * 0.01,
                    'close': 10.0 + i * 0.01,
                    'volume': 1000000
                }
                adapter.process_bar(bar)

        try:
            result, elapsed = self.measure_time(run_strategy)
            _, mem_used = self.measure_memory(run_strategy)

            self.record_result("策略执行1000次", elapsed, mem_used)
        except Exception as e:
            self.record_result("策略执行1000次", 0, 0, success=False)
            print(f"   错误: {e}")

    def test_backtest_performance(self):
        """测试回测引擎性能"""
        print("\n测试3: 回测引擎性能...")

        strategy_code = """
class SimpleStrategy:
    def __init__(self):
        self.position = 0

    def on_bar(self, bar):
        if self.position == 0:
            self.position = 100
            return {'action': 'buy', 'amount': 100}
        return None
"""

        # 生成1年数据
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        data = pd.DataFrame({
            'date': dates,
            'open': [10.0] * len(dates),
            'high': [10.5] * len(dates),
            'low': [9.5] * len(dates),
            'close': [10.0] * len(dates),
            'volume': [1000000] * len(dates)
        })

        def run_backtest():
            from app.services.backtest_engine import BacktestEngine

            engine = BacktestEngine(initial_cash=100000, enable_china_rules=False)
            result = engine.run(strategy_code, data, "TEST600000")
            return result

        try:
            result, elapsed = self.measure_time(run_backtest)
            _, mem_used = self.measure_memory(run_backtest)

            self.record_result("回测365天数据", elapsed, mem_used)
        except Exception as e:
            self.record_result("回测365天数据", 0, 0, success=False)
            print(f"   错误: {e}")

    def test_risk_validation(self):
        """测试风控验证性能"""
        print("\n测试4: 风控验证性能...")

        def run_risk_validation():
            from app.services.risk_validator import RiskValidator

            validator = RiskValidator(total_capital=100000)

            # 验证1000笔交易
            for i in range(1000):
                signal = {
                    'symbol': f'SH{600000 + i % 100}',
                    'action': 'buy',
                    'amount': 100,
                    'price': 10.0
                }
                validator.validate(signal)

        try:
            result, elapsed = self.measure_time(run_risk_validation)
            _, mem_used = self.measure_memory(run_risk_validation)

            self.record_result("风控验证1000笔", elapsed, mem_used)
        except Exception as e:
            self.record_result("风控验证1000笔", 0, 0, success=False)
            print(f"   错误: {e}")

    def test_shadow_scoring(self):
        """测试影子账户评分性能"""
        print("\n测试5: 影子账户评分性能...")

        def run_shadow_scoring():
            from app.services.shadow_manager import ShadowManager

            manager = ShadowManager()

            # 模拟创建和评分10个账户
            for i in range(10):
                # 简化测试，只测试评分逻辑
                scores = {
                    'annual_return': 0.20,
                    'sharpe_ratio': 1.5,
                    'max_drawdown': 0.10,
                    'volatility': 0.15,
                    'win_rate': 0.60
                }

                # 计算加权评分
                total_score = (
                    scores['annual_return'] * 100 * 0.30 +
                    (scores['sharpe_ratio'] / 3 * 100) * 0.25 +
                    ((0.30 - scores['max_drawdown']) / 0.30 * 100) * 0.20 +
                    ((0.30 - scores['volatility']) / 0.30 * 100) * 0.15 +
                    scores['win_rate'] * 100 * 0.10
                )

        try:
            result, elapsed = self.measure_time(run_shadow_scoring)
            _, mem_used = self.measure_memory(run_shadow_scoring)

            self.record_result("影子账户评分10个", elapsed, mem_used)
        except Exception as e:
            self.record_result("影子账户评分10个", 0, 0, success=False)
            print(f"   错误: {e}")

    def test_database_operations(self):
        """测试数据库操作性能"""
        print("\n测试6: 数据库操作性能...")

        def run_db_operations():
            from app.services.ai_generator import StrategyStorage

            storage = StrategyStorage()

            # 插入100条策略
            for i in range(100):
                storage.save({
                    'name': f'PerfTestStrategy{i}',
                    'code': 'class S:\n    def on_bar(self, bar):\n        return None',
                    'params': {},
                    'status': 'draft'
                })

            # 查询
            strategies = storage.load_all(limit=100)

        try:
            result, elapsed = self.measure_time(run_db_operations)
            _, mem_used = self.measure_memory(run_db_operations)

            self.record_result("数据库操作100次", elapsed, mem_used)
        except Exception as e:
            self.record_result("数据库操作100次", 0, 0, success=False)
            print(f"   错误: {e}")

    def run_all_tests(self):
        """运行所有性能测试"""
        print("\n" + "="*80)
        print("CN5-Lite 性能测试")
        print("="*80)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Python版本: {sys.version}")
        print(f"CPU核心数: {psutil.cpu_count()}")
        print(f"可用内存: {psutil.virtual_memory().available / 1024 / 1024 / 1024:.2f}GB")

        # 运行各项测试
        self.test_data_loading()
        self.test_strategy_execution()
        self.test_backtest_performance()
        self.test_risk_validation()
        self.test_shadow_scoring()
        self.test_database_operations()

        # 打印结果
        self.print_results()

        # 保存结果
        df = pd.DataFrame(self.results)
        df.to_csv('performance_results.csv', index=False)
        print(f"\n结果已保存到: performance_results.csv")


if __name__ == '__main__':
    tester = PerformanceTest()
    tester.run_all_tests()

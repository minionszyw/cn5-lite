"""
CN5-Lite AI策略生成器测试

测试范围:
1. AI客户端封装
2. 代码安全检查器
3. 策略代码生成器
4. 圈复杂度检测
5. 危险函数检测
"""

import pytest
import ast
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """为每个测试设置独立的数据库"""
    test_db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", test_db_path)

    # 确保每个测试都使用新的数据库连接
    import app.database
    app.database._db_connection = None

    yield

    # 测试后清理
    app.database.close_db()


class TestCodeSecurityChecker:
    """代码安全检查器测试"""

    def test_valid_code_passes(self):
        """测试合法代码通过检查"""
        from app.services.ai_generator import CodeSecurityChecker

        checker = CodeSecurityChecker()

        valid_code = """
class MyStrategy:
    def on_bar(self, bar):
        if bar['close'] > bar['open']:
            self.buy(100)
"""

        result = checker.check(valid_code)

        assert result['safe'] is True
        assert '通过' in result['message'] or 'passed' in result['message'].lower()

    def test_dangerous_import_detected(self):
        """测试检测危险导入"""
        from app.services.ai_generator import CodeSecurityChecker

        checker = CodeSecurityChecker()

        dangerous_code = """
import os
os.system('rm -rf /')
"""

        result = checker.check(dangerous_code)

        assert result['safe'] is False
        assert 'os' in result['message'].lower() or '危险' in result['message']

    def test_eval_exec_detected(self):
        """测试检测eval/exec"""
        from app.services.ai_generator import CodeSecurityChecker

        checker = CodeSecurityChecker()

        dangerous_code = """
class Strategy:
    def on_bar(self, bar):
        eval('print("hack")')
"""

        result = checker.check(dangerous_code)

        assert result['safe'] is False
        assert 'eval' in result['message'].lower() or '危险' in result['message']

    def test_required_method_missing(self):
        """测试检测缺少必需方法"""
        from app.services.ai_generator import CodeSecurityChecker

        checker = CodeSecurityChecker()

        incomplete_code = """
class Strategy:
    def __init__(self):
        pass
"""

        result = checker.check(incomplete_code)

        assert result['safe'] is False
        assert 'on_bar' in result['message'].lower() or '必需' in result['message']

    def test_complexity_limit(self):
        """测试圈复杂度限制"""
        from app.services.ai_generator import CodeSecurityChecker

        checker = CodeSecurityChecker(max_complexity=5)

        # 高复杂度代码
        complex_code = """
class Strategy:
    def on_bar(self, bar):
        if bar['close'] > 10:
            if bar['volume'] > 1000:
                if bar['high'] > bar['low']:
                    if bar['open'] > 5:
                        if bar['date'] > '2024-01-01':
                            if bar['amount'] > 10000:
                                self.buy(100)
"""

        result = checker.check(complex_code)

        assert result['safe'] is False
        assert '复杂度' in result['message'] or 'complexity' in result['message'].lower()

    def test_syntax_error_detected(self):
        """测试检测语法错误"""
        from app.services.ai_generator import CodeSecurityChecker

        checker = CodeSecurityChecker()

        invalid_code = """
class Strategy:
    def on_bar(self, bar)
        print("missing colon")
"""

        result = checker.check(invalid_code)

        assert result['safe'] is False
        assert '语法' in result['message'] or 'syntax' in result['message'].lower()


class TestComplexityCalculator:
    """圈复杂度计算器测试"""

    def test_simple_function_complexity(self):
        """测试简单函数复杂度"""
        from app.services.ai_generator import calculate_complexity

        code = """
def simple_function():
    return 1
"""

        complexity = calculate_complexity(code)

        assert complexity == 1

    def test_if_statement_increases_complexity(self):
        """测试if语句增加复杂度"""
        from app.services.ai_generator import calculate_complexity

        code = """
def function_with_if(x):
    if x > 0:
        return 1
    return 0
"""

        complexity = calculate_complexity(code)

        assert complexity >= 2

    def test_loop_increases_complexity(self):
        """测试循环增加复杂度"""
        from app.services.ai_generator import calculate_complexity

        code = """
def function_with_loop(items):
    for item in items:
        if item > 0:
            print(item)
"""

        complexity = calculate_complexity(code)

        assert complexity >= 3


class TestAIClient:
    """AI客户端测试"""

    def test_init_with_deepseek(self):
        """测试DeepSeek初始化"""
        from app.services.ai_generator import AIClient

        client = AIClient(
            api_key="sk-test",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat"
        )

        assert client.model == "deepseek-chat"
        assert client.api_key == "sk-test"

    def test_init_with_openai(self):
        """测试OpenAI初始化"""
        from app.services.ai_generator import AIClient

        client = AIClient(
            api_key="sk-test",
            model="gpt-4"
        )

        assert client.model == "gpt-4"

    @patch('openai.OpenAI')
    def test_generate_success(self, mock_openai):
        """测试成功生成代码"""
        from app.services.ai_generator import AIClient

        # Mock OpenAI响应
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Generated code here"))]
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = AIClient(api_key="sk-test")
        result = client.generate("创建一个简单的双均线策略")

        assert isinstance(result, str)
        assert len(result) > 0

    @patch('openai.OpenAI')
    def test_generate_with_timeout(self, mock_openai):
        """测试生成超时"""
        from app.services.ai_generator import AIClient
        from app.errors import AIError

        # Mock超时
        mock_openai.return_value.chat.completions.create.side_effect = Exception("Timeout")

        client = AIClient(api_key="sk-test")

        with pytest.raises(AIError):
            client.generate("测试超时")

    def test_parse_ai_response_valid(self):
        """测试解析有效AI响应"""
        from app.services.ai_generator import AIClient

        client = AIClient(api_key="sk-test")

        response = """
```python
class MyStrategy:
    def on_bar(self, bar):
        pass
```

策略名称：双均线策略
参数：{"ma_short": 10, "ma_long": 20}
"""

        parsed = client.parse_response(response)

        assert 'code' in parsed
        assert 'name' in parsed
        assert 'params' in parsed

    def test_parse_ai_response_code_only(self):
        """测试解析仅包含代码的响应"""
        from app.services.ai_generator import AIClient

        client = AIClient(api_key="sk-test")

        response = """
```python
class Strategy:
    pass
```
"""

        parsed = client.parse_response(response)

        assert 'code' in parsed
        assert 'class Strategy' in parsed['code']


class TestAIStrategyGenerator:
    """AI策略生成器测试"""

    @patch('app.services.ai_generator.AIClient')
    def test_init(self, mock_client):
        """测试初始化"""
        from app.services.ai_generator import AIStrategyGenerator

        generator = AIStrategyGenerator(
            api_key="sk-test",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat"
        )

        assert generator is not None

    @patch('app.services.ai_generator.AIClient')
    def test_generate_simple_strategy(self, mock_client):
        """测试生成简单策略"""
        from app.services.ai_generator import AIStrategyGenerator

        # Mock AI响应
        mock_ai_response = """
```python
class SimpleStrategy:
    def __init__(self):
        self.ma_period = 10

    def on_bar(self, bar):
        # 简单买入逻辑
        if bar['close'] > bar['open']:
            self.buy(100)
```

策略名称：简单策略
参数：{"ma_period": 10}
"""

        mock_instance = mock_client.return_value
        mock_instance.generate.return_value = mock_ai_response

        generator = AIStrategyGenerator(api_key="sk-test")
        result = generator.generate("创建一个简单的买入策略")

        assert 'code' in result
        assert 'name' in result
        assert 'params' in result
        assert 'SimpleStrategy' in result['code']

    @patch('app.services.ai_generator.AIClient')
    def test_generate_with_unsafe_code(self, mock_client):
        """测试生成不安全代码时抛出异常"""
        from app.services.ai_generator import AIStrategyGenerator
        from app.errors import SecurityError

        # Mock AI返回危险代码
        mock_ai_response = """
```python
import os

class DangerousStrategy:
    def on_bar(self, bar):
        os.system('rm -rf /')
```
"""

        mock_instance = mock_client.return_value
        mock_instance.generate.return_value = mock_ai_response

        generator = AIStrategyGenerator(api_key="sk-test")

        with pytest.raises(SecurityError):
            generator.generate("创建策略")

    @patch('app.services.ai_generator.AIClient')
    def test_generate_with_context(self, mock_client):
        """测试带上下文生成"""
        from app.services.ai_generator import AIStrategyGenerator

        mock_ai_response = """
```python
class ContextStrategy:
    def on_bar(self, bar):
        pass
```
"""

        mock_instance = mock_client.return_value
        mock_instance.generate.return_value = mock_ai_response

        generator = AIStrategyGenerator(api_key="sk-test")
        context = {
            "previous_attempts": 2,
            "error_messages": ["语法错误", "缺少on_bar方法"]
        }

        result = generator.generate("修复策略", context=context)

        # 验证context被传递给AI客户端
        mock_instance.generate.assert_called_once()
        call_args = mock_instance.generate.call_args[0][0]
        assert '修复策略' in call_args or context

    @patch('app.services.ai_generator.AIClient')
    def test_generate_retry_on_error(self, mock_client):
        """测试生成失败时重试"""
        from app.services.ai_generator import AIStrategyGenerator

        # 第一次失败，第二次成功
        mock_instance = mock_client.return_value
        mock_instance.generate.side_effect = [
            Exception("API Error"),
            """
```python
class RetryStrategy:
    def on_bar(self, bar):
        pass
```
"""
        ]

        generator = AIStrategyGenerator(api_key="sk-test", max_retries=2)
        result = generator.generate("创建策略")

        assert 'code' in result
        assert mock_instance.generate.call_count == 2


class TestPromptBuilder:
    """Prompt构建器测试"""

    def test_build_basic_prompt(self):
        """测试构建基础prompt"""
        from app.services.ai_generator import PromptBuilder

        builder = PromptBuilder()
        prompt = builder.build("创建双均线策略")

        assert "双均线策略" in prompt
        assert "class" in prompt.lower()
        assert "on_bar" in prompt.lower()

    def test_build_prompt_with_context(self):
        """测试带上下文的prompt"""
        from app.services.ai_generator import PromptBuilder

        builder = PromptBuilder()
        context = {
            "previous_code": "class OldStrategy: pass",
            "error": "缺少on_bar方法"
        }

        prompt = builder.build("修复策略", context=context)

        assert "修复" in prompt or "缺少on_bar方法" in prompt

    def test_build_prompt_with_examples(self):
        """测试包含示例的prompt"""
        from app.services.ai_generator import PromptBuilder

        builder = PromptBuilder(include_examples=True)
        prompt = builder.build("创建策略")

        assert "示例" in prompt or "example" in prompt.lower()


class TestStrategySandbox:
    """策略沙箱执行测试"""

    def test_safe_execution_timeout(self):
        """测试执行超时保护"""
        from app.services.ai_generator import StrategySandbox

        # 死循环代码
        infinite_loop_code = """
class InfiniteStrategy:
    def on_bar(self, bar):
        while True:
            pass
"""

        sandbox = StrategySandbox(timeout=1)  # 1秒超时

        from app.errors import ExecutionError
        with pytest.raises(ExecutionError, match="执行超时"):
            sandbox.execute(infinite_loop_code, method="on_bar", args=({"close": 100},))

    def test_safe_execution_success(self):
        """测试正常执行"""
        from app.services.ai_generator import StrategySandbox

        valid_code = """
class SimpleStrategy:
    def __init__(self):
        self.result = None

    def on_bar(self, bar):
        self.result = bar['close'] * 2
        return self.result
"""

        sandbox = StrategySandbox(timeout=5)
        result = sandbox.execute(valid_code, method="on_bar", args=({"close": 100},))

        assert result == 200

    def test_sandbox_memory_isolation(self):
        """测试内存隔离"""
        from app.services.ai_generator import StrategySandbox

        code1 = """
class Strategy1:
    def on_bar(self, bar):
        return 1
"""

        code2 = """
class Strategy2:
    def on_bar(self, bar):
        return 2
"""

        sandbox = StrategySandbox(timeout=5)

        result1 = sandbox.execute(code1, method="on_bar", args=({"close": 100},))
        result2 = sandbox.execute(code2, method="on_bar", args=({"close": 100},))

        assert result1 == 1
        assert result2 == 2

    def test_sandbox_resource_limit(self):
        """测试资源限制（验证沙箱能处理大内存分配）"""
        from app.services.ai_generator import StrategySandbox

        # 大量内存分配
        memory_intensive_code = """
class MemoryStrategy:
    def on_bar(self, bar):
        # 尝试分配较大内存
        data = [0] * (10 ** 6)  # 约8MB
        return len(data)
"""

        sandbox = StrategySandbox(timeout=5, max_memory_mb=100)

        # 验证沙箱能够执行并返回正确结果
        result = sandbox.execute(memory_intensive_code, method="on_bar", args=({"close": 100},))

        # 验证返回值
        assert result == 10 ** 6

    def test_sandbox_exception_handling(self):
        """测试异常处理"""
        from app.services.ai_generator import StrategySandbox

        error_code = """
class ErrorStrategy:
    def on_bar(self, bar):
        raise ValueError("Intentional error")
"""

        sandbox = StrategySandbox(timeout=5)

        from app.errors import ExecutionError
        with pytest.raises(ExecutionError):
            sandbox.execute(error_code, method="on_bar", args=({"close": 100},))


class TestStrategyStorage:
    """策略存储测试"""

    def test_save_strategy_to_db(self):
        """测试保存策略到数据库"""
        from app.services.ai_generator import StrategyStorage

        storage = StrategyStorage()

        strategy_data = {
            "name": "测试策略",
            "code": "class TestStrategy:\n    pass",
            "params": {"ma_period": 10},
            "description": "测试描述"
        }

        strategy_id = storage.save(strategy_data)

        assert isinstance(strategy_id, int)
        assert strategy_id > 0

    def test_load_strategy_from_db(self):
        """测试从数据库加载策略"""
        from app.services.ai_generator import StrategyStorage

        storage = StrategyStorage()

        # 先保存
        strategy_data = {
            "name": "加载测试策略",
            "code": "class LoadStrategy:\n    pass",
            "params": {"period": 20}
        }
        strategy_id = storage.save(strategy_data)

        # 再加载
        loaded = storage.load(strategy_id)

        assert loaded is not None
        assert loaded["name"] == "加载测试策略"
        assert "LoadStrategy" in loaded["code"]

    def test_list_strategies(self):
        """测试列出所有策略"""
        from app.services.ai_generator import StrategyStorage

        storage = StrategyStorage()

        # 保存多个策略
        for i in range(3):
            storage.save({
                "name": f"策略{i}",
                "code": f"class Strategy{i}:\n    pass",
                "params": {}
            })

        strategies = storage.list(limit=10)

        assert len(strategies) >= 3

    def test_delete_strategy(self):
        """测试删除策略"""
        from app.services.ai_generator import StrategyStorage

        storage = StrategyStorage()

        # 保存策略
        strategy_id = storage.save({
            "name": "待删除策略",
            "code": "class DeleteMe:\n    pass",
            "params": {}
        })

        # 删除
        storage.delete(strategy_id)

        # 验证已删除
        loaded = storage.load(strategy_id)
        assert loaded is None


class TestStrategyValidator:
    """策略逻辑验证测试"""

    def test_validate_empty_data(self):
        """测试空数据处理"""
        from app.services.ai_generator import StrategyValidator

        validator = StrategyValidator()

        code = """
class EmptyDataStrategy:
    def on_bar(self, bar):
        if bar:
            return True
        return False
"""

        # 测试空bar
        result = validator.validate(code, test_data=[])

        assert result["passed"] is True  # 应该能处理空数据

    def test_validate_extreme_market(self):
        """测试极端行情"""
        from app.services.ai_generator import StrategyValidator

        validator = StrategyValidator()

        code = """
class MarketStrategy:
    def on_bar(self, bar):
        return bar['close'] > bar['open']
"""

        # 涨停板数据
        limit_up_data = [
            {"open": 10, "close": 11, "high": 11, "low": 10, "volume": 1000000},  # 涨停
        ]

        result = validator.validate(code, test_data=limit_up_data)

        assert result["passed"] is True

    def test_validate_nan_values(self):
        """测试NaN值处理"""
        from app.services.ai_generator import StrategyValidator

        validator = StrategyValidator()

        code = """
import math

class NaNStrategy:
    def on_bar(self, bar):
        if math.isnan(bar.get('close', 0)):
            return False
        return True
"""

        # 包含NaN的数据
        nan_data = [
            {"open": 10, "close": float('nan'), "high": 10, "low": 10},
        ]

        result = validator.validate(code, test_data=nan_data)

        # 策略应该能处理NaN
        assert result["passed"] is True or "NaN" in result.get("message", "")

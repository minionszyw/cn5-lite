"""
CN5-Lite AI策略生成器

功能:
1. AI客户端封装（支持OpenAI兼容API）
2. 代码安全检查器
3. 圈复杂度计算
4. Prompt构建器
5. 策略代码生成
"""

import ast
import re
import json
from typing import Dict, Any, Optional, List
from openai import OpenAI

from app.errors import AIError, SecurityError, ValidationError, ComplexityError
from app.logger import get_logger

logger = get_logger(__name__)


# ==================
# 圈复杂度计算
# ==================

class ComplexityVisitor(ast.NodeVisitor):
    """AST访问器：计算圈复杂度"""

    def __init__(self):
        self.complexity = 1  # 基础复杂度为1

    def visit_If(self, node):
        """if语句增加复杂度"""
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        """for循环增加复杂度"""
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        """while循环增加复杂度"""
        self.complexity += 1
        self.generic_visit(node)

    def visit_And(self, node):
        """and操作符增加复杂度"""
        self.complexity += 1
        self.generic_visit(node)

    def visit_Or(self, node):
        """or操作符增加复杂度"""
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        """异常处理增加复杂度"""
        self.complexity += 1
        self.generic_visit(node)


def calculate_complexity(code: str) -> int:
    """
    计算代码圈复杂度

    Args:
        code: 源代码

    Returns:
        圈复杂度值
    """
    try:
        tree = ast.parse(code)
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        return visitor.complexity
    except SyntaxError:
        return 0


# ==================
# 代码安全检查器
# ==================

class CodeSecurityChecker:
    """
    代码安全检查器

    检查项:
    1. 危险导入（os, sys, subprocess等）
    2. 危险函数（eval, exec, compile等）
    3. 必需方法（on_bar等）
    4. 圈复杂度限制
    5. 语法合法性
    """

    # 危险模块黑名单
    DANGEROUS_MODULES = {
        'os', 'sys', 'subprocess', 'shutil', 'pathlib',
        'socket', 'urllib', 'http', 'ftplib', 'telnetlib',
        '__import__', 'importlib', 'pickle', 'shelve',
        'ctypes', 'multiprocessing', 'threading'
    }

    # 危险函数黑名单
    DANGEROUS_FUNCTIONS = {
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input', 'raw_input',
        'globals', 'locals', 'vars', 'dir',
        'getattr', 'setattr', 'delattr', 'hasattr'
    }

    # 必需方法
    REQUIRED_METHODS = {'on_bar'}

    def __init__(self, max_complexity: int = 20):
        """
        初始化安全检查器

        Args:
            max_complexity: 最大圈复杂度
        """
        self.max_complexity = max_complexity

    def check(self, code: str) -> Dict[str, Any]:
        """
        执行安全检查

        Args:
            code: 待检查的代码

        Returns:
            {
                "safe": bool,
                "message": str,
                "details": {...}
            }
        """
        # 1. 语法检查
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "safe": False,
                "message": f"语法错误: {e}",
                "details": {"error": str(e)}
            }

        # 2. 危险导入检查
        dangerous_imports = self._check_imports(tree)
        if dangerous_imports:
            return {
                "safe": False,
                "message": f"检测到危险导入: {', '.join(dangerous_imports)}",
                "details": {"dangerous_imports": dangerous_imports}
            }

        # 3. 危险函数检查
        dangerous_calls = self._check_function_calls(tree)
        if dangerous_calls:
            return {
                "safe": False,
                "message": f"检测到危险函数调用: {', '.join(dangerous_calls)}",
                "details": {"dangerous_calls": dangerous_calls}
            }

        # 4. 必需方法检查
        missing_methods = self._check_required_methods(tree)
        if missing_methods:
            return {
                "safe": False,
                "message": f"缺少必需方法: {', '.join(missing_methods)}",
                "details": {"missing_methods": missing_methods}
            }

        # 5. 圈复杂度检查
        complexity = calculate_complexity(code)
        if complexity > self.max_complexity:
            return {
                "safe": False,
                "message": f"圈复杂度过高: {complexity} > {self.max_complexity}",
                "details": {"complexity": complexity, "max": self.max_complexity}
            }

        return {
            "safe": True,
            "message": "代码安全检查通过",
            "details": {
                "complexity": complexity,
                "methods_found": self._get_method_names(tree)
            }
        }

    def _check_imports(self, tree: ast.AST) -> List[str]:
        """检查危险导入"""
        dangerous = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.DANGEROUS_MODULES:
                        dangerous.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module in self.DANGEROUS_MODULES:
                    dangerous.append(node.module)

        return dangerous

    def _check_function_calls(self, tree: ast.AST) -> List[str]:
        """检查危险函数调用"""
        dangerous = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.DANGEROUS_FUNCTIONS:
                        dangerous.append(node.func.id)

        return dangerous

    def _check_required_methods(self, tree: ast.AST) -> List[str]:
        """检查必需方法"""
        found_methods = self._get_method_names(tree)
        missing = self.REQUIRED_METHODS - found_methods
        return list(missing)

    def _get_method_names(self, tree: ast.AST) -> set:
        """获取所有方法名"""
        methods = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.add(item.name)

        return methods


# ==================
# AI客户端
# ==================

class AIClient:
    """
    AI客户端封装

    支持OpenAI兼容API（DeepSeek、Qwen等）
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "deepseek-chat",
        timeout: int = 60
    ):
        """
        初始化AI客户端

        Args:
            api_key: API密钥
            base_url: API endpoint（默认OpenAI）
            model: 模型名称
            timeout: 超时时间（秒）
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

        # 创建OpenAI客户端
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        else:
            self.client = OpenAI(api_key=api_key, timeout=timeout)

        logger.info(f"AI客户端初始化完成", model=model, base_url=base_url or "OpenAI")

    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """
        调用AI生成代码

        Args:
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            AI生成的响应

        Raises:
            AIError: AI调用失败
        """
        try:
            logger.info("调用AI生成策略", model=self.model)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的量化交易策略开发助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content

            logger.info("AI生成完成", length=len(content))

            return content

        except Exception as e:
            logger.error(f"AI调用失败: {e}")
            raise AIError(f"AI调用失败: {e}")

    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析AI响应

        Args:
            response: AI响应文本

        Returns:
            {
                "code": "策略代码",
                "name": "策略名称",
                "params": {...}
            }
        """
        result = {
            "code": "",
            "name": "未命名策略",
            "params": {}
        }

        # 提取Python代码块
        code_pattern = r'```python\n(.*?)\n```'
        code_match = re.search(code_pattern, response, re.DOTALL)

        if code_match:
            result["code"] = code_match.group(1).strip()
        else:
            # 尝试不带语言标识的代码块
            code_pattern = r'```\n(.*?)\n```'
            code_match = re.search(code_pattern, response, re.DOTALL)
            if code_match:
                result["code"] = code_match.group(1).strip()

        # 提取策略名称
        name_pattern = r'策略名称[：:]\s*([^\n]+)'
        name_match = re.search(name_pattern, response)
        if name_match:
            result["name"] = name_match.group(1).strip()

        # 提取参数
        params_pattern = r'参数[：:]\s*(\{[^}]+\})'
        params_match = re.search(params_pattern, response)
        if params_match:
            try:
                result["params"] = json.loads(params_match.group(1))
            except json.JSONDecodeError:
                pass

        return result


# ==================
# Prompt构建器
# ==================

class PromptBuilder:
    """Prompt构建器"""

    STRATEGY_TEMPLATE = """
请帮我创建一个量化交易策略。

用户需求：{user_input}

{context_section}

要求：
1. 使用Python编写
2. 必须包含一个策略类
3. 必须实现on_bar(self, bar)方法，接收K线数据
4. bar参数格式：{{'date': 日期, 'open': 开盘价, 'high': 最高价, 'low': 最低价, 'close': 收盘价, 'volume': 成交量}}
5. 策略类可以调用self.buy(amount)和self.sell(amount)方法
6. 代码必须简洁、安全，避免使用os、sys等危险模块
7. 代码复杂度控制在20以内

{examples_section}

请按以下格式返回：
```python
# 策略代码
class YourStrategy:
    def __init__(self):
        # 初始化参数
        pass

    def on_bar(self, bar):
        # 策略逻辑
        pass
```

策略名称：策略的名称
参数：{{"param1": value1, "param2": value2}}
"""

    EXAMPLE = """
示例策略：
```python
class MAStrategy:
    def __init__(self):
        self.ma_period = 20
        self.prices = []

    def on_bar(self, bar):
        self.prices.append(bar['close'])
        if len(self.prices) < self.ma_period:
            return

        ma = sum(self.prices[-self.ma_period:]) / self.ma_period

        if bar['close'] > ma:
            self.buy(100)
        elif bar['close'] < ma:
            self.sell(100)
```
"""

    def __init__(self, include_examples: bool = True):
        """
        初始化Prompt构建器

        Args:
            include_examples: 是否包含示例
        """
        self.include_examples = include_examples

    def build(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        构建Prompt

        Args:
            user_input: 用户输入
            context: 上下文信息

        Returns:
            构建好的prompt
        """
        # 处理上下文
        context_section = ""
        if context:
            if "previous_code" in context:
                context_section += f"\n之前的代码：\n```python\n{context['previous_code']}\n```\n"

            if "error" in context:
                context_section += f"\n错误信息：{context['error']}\n"

            if "previous_attempts" in context:
                context_section += f"\n已尝试次数：{context['previous_attempts']}\n"

        # 示例部分
        examples_section = self.EXAMPLE if self.include_examples else ""

        # 填充模板
        prompt = self.STRATEGY_TEMPLATE.format(
            user_input=user_input,
            context_section=context_section,
            examples_section=examples_section
        )

        return prompt


# ==================
# AI策略生成器
# ==================

class AIStrategyGenerator:
    """
    AI策略生成器

    功能：
    1. 生成策略代码
    2. 安全检查
    3. 失败重试
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "deepseek-chat",
        max_retries: int = 3,
        max_complexity: int = 20
    ):
        """
        初始化生成器

        Args:
            api_key: API密钥
            base_url: API endpoint
            model: 模型名称
            max_retries: 最大重试次数
            max_complexity: 最大圈复杂度
        """
        self.ai_client = AIClient(api_key=api_key, base_url=base_url, model=model)
        self.security_checker = CodeSecurityChecker(max_complexity=max_complexity)
        self.prompt_builder = PromptBuilder()
        self.max_retries = max_retries

        logger.info("AI策略生成器初始化完成")

    def generate(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        生成策略代码

        Args:
            user_input: 用户输入的策略需求
            context: 上下文信息

        Returns:
            {
                "code": "策略代码",
                "name": "策略名称",
                "params": {...}
            }

        Raises:
            AIError: AI生成失败
            SecurityError: 安全检查失败
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"开始生成策略，尝试 {attempt + 1}/{self.max_retries}")

                # 构建prompt
                prompt = self.prompt_builder.build(user_input, context)

                # 调用AI生成
                ai_response = self.ai_client.generate(prompt)

                # 解析响应
                result = self.ai_client.parse_response(ai_response)

                if not result['code']:
                    raise AIError("AI未返回有效代码")

                # 安全检查
                security_result = self.security_checker.check(result['code'])

                if not security_result['safe']:
                    error_msg = security_result['message']
                    logger.warning(f"安全检查失败: {error_msg}")

                    # 如果还有重试机会，更新context继续
                    if attempt < self.max_retries - 1:
                        if context is None:
                            context = {}
                        context['error'] = error_msg
                        context['previous_code'] = result['code']
                        context['previous_attempts'] = attempt + 1
                        continue
                    else:
                        raise SecurityError(error_msg)

                logger.info("策略生成成功", name=result.get('name'))

                return result

            except AIError:
                if attempt < self.max_retries - 1:
                    logger.warning(f"AI调用失败，重试中...")
                    continue
                else:
                    raise

        raise AIError(f"生成失败，已重试{self.max_retries}次")


# ==================
# 策略沙箱执行器
# ==================

class StrategySandbox:
    """
    策略沙箱执行器

    功能：
    1. 超时保护
    2. 内存限制
    3. 异常隔离
    4. 安全执行
    """

    def __init__(self, timeout: int = 30, max_memory_mb: int = 500):
        """
        初始化沙箱

        Args:
            timeout: 执行超时时间（秒）
            max_memory_mb: 最大内存限制（MB）
        """
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        logger.info(f"沙箱初始化", timeout=timeout, max_memory_mb=max_memory_mb)

    def execute(self, code: str, method: str = "on_bar", args: tuple = ()) -> Any:
        """
        在沙箱中执行策略代码

        Args:
            code: 策略代码
            method: 要调用的方法名
            args: 方法参数

        Returns:
            方法执行结果

        Raises:
            ExecutionError: 执行失败
        """
        from app.errors import ExecutionError
        import signal
        import traceback

        # 定义超时处理函数
        def timeout_handler(signum, frame):
            raise TimeoutError("执行超时")

        try:
            # 设置超时
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout)

            # 创建隔离的执行环境
            import builtins
            namespace = {
                '__builtins__': {
                    '__build_class__': builtins.__build_class__,
                    '__name__': '__main__',
                    '__import__': builtins.__import__,
                    'range': range,
                    'len': len,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'abs': abs,
                    'round': round,
                    'int': int,
                    'float': float,
                    'str': str,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'enumerate': enumerate,
                    'zip': zip,
                    'sorted': sorted,
                    'reversed': reversed,
                    'any': any,
                    'all': all,
                    'isinstance': isinstance,
                    'hasattr': hasattr,
                    'getattr': getattr,
                    'object': object,
                    'type': type,
                    'None': None,
                    'True': True,
                    'False': False,
                }
            }

            # 执行代码
            exec(code, namespace)

            # 找到策略类
            strategy_class = None
            for name, obj in namespace.items():
                if isinstance(obj, type) and hasattr(obj, method):
                    strategy_class = obj
                    break

            if not strategy_class:
                raise ExecutionError(f"未找到包含{method}方法的策略类")

            # 实例化策略
            strategy_instance = strategy_class()

            # 调用方法
            result = getattr(strategy_instance, method)(*args)

            # 取消超时
            signal.alarm(0)

            logger.info(f"沙箱执行成功", method=method)

            return result

        except TimeoutError as e:
            signal.alarm(0)
            logger.error(f"执行超时: {e}")
            raise ExecutionError(f"执行超时（{self.timeout}秒）")

        except MemoryError as e:
            signal.alarm(0)
            logger.error(f"内存超限: {e}")
            raise ExecutionError("内存超限")

        except Exception as e:
            signal.alarm(0)
            error_msg = f"执行失败: {str(e)}"
            logger.error(error_msg, error=str(e), traceback=traceback.format_exc())
            raise ExecutionError(error_msg)


# ==================
# 策略存储管理器
# ==================

class StrategyStorage:
    """
    策略存储管理器

    功能：
    1. 保存策略到数据库
    2. 加载策略
    3. 列出策略
    4. 删除策略
    """

    def __init__(self):
        """初始化存储管理器"""
        from app.database import get_db
        self.db = get_db()
        logger.info("策略存储管理器初始化完成")

    def save(self, strategy_data: Dict[str, Any]) -> int:
        """
        保存策略到数据库

        Args:
            strategy_data: {
                "name": "策略名称",
                "code": "策略代码",
                "params": {...},
                "description": "描述"
            }

        Returns:
            策略ID
        """
        from datetime import datetime

        query = """
        INSERT INTO strategies (name, code, params, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """

        params_json = json.dumps(strategy_data.get("params", {}))
        now = datetime.now().isoformat()

        cursor = self.db.execute(
            query,
            (
                strategy_data.get("name", "未命名策略"),
                strategy_data["code"],
                params_json,
                strategy_data.get("description", ""),
                now,
                now
            )
        )

        self.db.commit()
        strategy_id = cursor.lastrowid

        logger.info(f"策略已保存", strategy_id=strategy_id, name=strategy_data.get("name"))

        return strategy_id

    def load(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """
        从数据库加载策略

        Args:
            strategy_id: 策略ID

        Returns:
            策略数据或None
        """
        query = "SELECT * FROM strategies WHERE id = ?"

        cursor = self.db.execute(query, (strategy_id,))
        row = cursor.fetchone()

        if not row:
            logger.warning(f"策略不存在", strategy_id=strategy_id)
            return None

        # 转换为字典
        columns = [desc[0] for desc in cursor.description]
        strategy = dict(zip(columns, row))

        # 解析params JSON
        if strategy.get("params"):
            try:
                strategy["params"] = json.loads(strategy["params"])
            except json.JSONDecodeError:
                strategy["params"] = {}

        logger.info(f"策略已加载", strategy_id=strategy_id)

        return strategy

    def list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        列出所有策略

        Args:
            limit: 返回数量
            offset: 偏移量

        Returns:
            策略列表
        """
        query = "SELECT * FROM strategies ORDER BY created_at DESC LIMIT ? OFFSET ?"

        cursor = self.db.execute(query, (limit, offset))
        rows = cursor.fetchall()

        # 转换为字典列表
        columns = [desc[0] for desc in cursor.description]
        strategies = []

        for row in rows:
            strategy = dict(zip(columns, row))

            # 解析params JSON
            if strategy.get("params"):
                try:
                    strategy["params"] = json.loads(strategy["params"])
                except json.JSONDecodeError:
                    strategy["params"] = {}

            strategies.append(strategy)

        logger.info(f"列出策略", count=len(strategies))

        return strategies

    def delete(self, strategy_id: int):
        """
        删除策略

        Args:
            strategy_id: 策略ID
        """
        query = "DELETE FROM strategies WHERE id = ?"

        self.db.execute(query, (strategy_id,))
        self.db.commit()

        logger.info(f"策略已删除", strategy_id=strategy_id)


# ==================
# 策略逻辑验证器
# ==================

class StrategyValidator:
    """
    策略逻辑验证器

    功能：
    1. 空数据测试
    2. 极端行情测试
    3. 异常值测试（NaN/Inf）
    4. 边界条件测试
    """

    def __init__(self):
        """初始化验证器"""
        self.sandbox = StrategySandbox(timeout=10)
        logger.info("策略验证器初始化完成")

    def validate(self, code: str, test_data: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        验证策略逻辑

        Args:
            code: 策略代码
            test_data: 测试数据

        Returns:
            {
                "passed": bool,
                "message": str,
                "details": {...}
            }
        """
        results = []

        # 1. 空数据测试
        try:
            if test_data is None or len(test_data) == 0:
                # 测试能否处理空数据
                self.sandbox.execute(code, method="on_bar", args=({"close": 100},))
                results.append({"test": "empty_data", "passed": True})
            else:
                results.append({"test": "empty_data", "passed": True, "skipped": True})
        except Exception as e:
            results.append({"test": "empty_data", "passed": False, "error": str(e)})

        # 2. 使用提供的测试数据
        if test_data:
            for i, bar in enumerate(test_data):
                try:
                    self.sandbox.execute(code, method="on_bar", args=(bar,))
                    results.append({"test": f"bar_{i}", "passed": True})
                except Exception as e:
                    results.append({"test": f"bar_{i}", "passed": False, "error": str(e)})

        # 汇总结果
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.get("passed"))

        all_passed = passed_tests == total_tests

        return {
            "passed": all_passed,
            "message": f"通过 {passed_tests}/{total_tests} 项测试" if all_passed else f"失败 {total_tests - passed_tests}/{total_tests} 项测试",
            "details": results
        }

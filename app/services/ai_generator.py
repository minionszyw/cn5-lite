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

"""
CN5-Lite 自定义异常体系
"""


class CN5Error(Exception):
    """CN5系统基础异常类"""
    pass


# ==================
# 数据源相关异常
# ==================

class DataSourceError(CN5Error):
    """数据源异常"""
    pass


class DataValidationError(CN5Error):
    """数据验证异常"""
    pass


# ==================
# AI相关异常
# ==================

class AIError(CN5Error):
    """AI服务异常"""
    pass


class SecurityError(CN5Error):
    """安全检查异常"""
    pass


class ValidationError(CN5Error):
    """验证异常"""
    pass


class ComplexityError(CN5Error):
    """复杂度超标异常"""
    pass


class ExecutionError(CN5Error):
    """代码执行异常"""
    pass


# ==================
# 回测相关异常
# ==================

class BacktestError(CN5Error):
    """回测异常"""
    pass


# ==================
# 风控相关异常
# ==================

class RiskError(CN5Error):
    """风控异常"""
    pass


# ==================
# 配置相关异常
# ==================

class ConfigError(CN5Error):
    """配置异常"""
    pass


# ==================
# 交易相关异常
# ==================

class TradingError(CN5Error):
    """交易异常"""
    pass

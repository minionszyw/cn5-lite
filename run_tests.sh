#!/bin/bash
# CN5-Lite 测试运行脚本

set -e

echo "========================================="
echo "CN5-Lite 单元测试"
echo "========================================="

# 运行单元测试
echo "运行单元测试..."
pytest tests/unit/test_multi_datasource.py -v \
    --cov=app/services/multi_datasource \
    --cov-report=term-missing \
    --cov-report=html \
    --tb=short

echo ""
echo "========================================="
echo "测试完成！"
echo "========================================="
echo "覆盖率报告已生成: htmlcov/index.html"

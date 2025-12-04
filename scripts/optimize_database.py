"""
数据库优化脚本
优化SQLite数据库性能

运行方式：
  python scripts/optimize_database.py
"""

import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db_path


def optimize_database():
    """优化SQLite数据库"""
    db_path = get_db_path()

    print(f"\n{'='*60}")
    print("CN5-Lite 数据库优化工具")
    print(f"{'='*60}")
    print(f"数据库路径: {db_path}")

    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 分析数据库
    print("\n步骤1: 分析数据库...")
    cursor.execute("ANALYZE")
    print("✅ 数据库分析完成")

    # 2. 清理vacuum
    print("\n步骤2: 清理vacuum...")
    initial_size = os.path.getsize(db_path) / 1024 / 1024  # MB
    print(f"   初始大小: {initial_size:.2f}MB")

    cursor.execute("VACUUM")

    final_size = os.path.getsize(db_path) / 1024 / 1024  # MB
    saved = initial_size - final_size
    print(f"   优化后: {final_size:.2f}MB")
    print(f"   节省: {saved:.2f}MB ({saved/initial_size*100:.1f}%)")

    # 3. 创建索引
    print("\n步骤3: 创建/优化索引...")

    indexes = [
        ("idx_strategies_status", "strategies", "status"),
        ("idx_strategies_created", "strategies", "created_at"),
        ("idx_backtest_strategy", "backtest_results", "strategy_id"),
        ("idx_backtest_date", "backtest_results", "start_date, end_date"),
        ("idx_trades_symbol", "trades", "symbol"),
        ("idx_trades_date", "trades", "trade_time"),
        ("idx_trades_strategy", "trades", "strategy_id"),
        ("idx_shadow_status", "shadow_accounts", "status"),
        ("idx_shadow_ranking", "shadow_accounts", "ranking"),
        ("idx_shadow_score", "shadow_accounts", "weighted_score DESC"),
    ]

    for idx_name, table, columns in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
            print(f"   ✅ {idx_name}")
        except sqlite3.Error as e:
            print(f"   ⚠️  {idx_name}: {e}")

    # 4. 优化配置
    print("\n步骤4: 优化配置...")

    optimizations = [
        ("PRAGMA journal_mode=WAL", "启用WAL模式"),
        ("PRAGMA synchronous=NORMAL", "设置同步模式"),
        ("PRAGMA cache_size=-64000", "设置缓存64MB"),
        ("PRAGMA temp_store=MEMORY", "临时存储在内存"),
        ("PRAGMA mmap_size=268435456", "启用内存映射256MB"),
    ]

    for pragma, desc in optimizations:
        try:
            cursor.execute(pragma)
            print(f"   ✅ {desc}")
        except sqlite3.Error as e:
            print(f"   ⚠️  {desc}: {e}")

    # 5. 统计信息
    print("\n步骤5: 数据库统计...")

    tables = ['strategies', 'backtest_results', 'trades', 'shadow_accounts']

    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   {table}: {count}条记录")
        except sqlite3.Error:
            print(f"   {table}: 表不存在")

    # 6. 完整性检查
    print("\n步骤6: 完整性检查...")
    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()[0]

    if result == "ok":
        print("   ✅ 数据库完整性正常")
    else:
        print(f"   ❌ 数据库完整性问题: {result}")

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print("✅ 数据库优化完成")
    print(f"{'='*60}\n")


def show_database_info():
    """显示数据库信息"""
    db_path = get_db_path()

    if not os.path.exists(db_path):
        print("数据库文件不存在")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n数据库信息:")
    print("-" * 60)

    # 表列表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"表数量: {len(tables)}")
    for table in tables:
        print(f"  - {table[0]}")

    # 索引列表
    print("\n索引:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = cursor.fetchall()
    for idx in indexes:
        print(f"  - {idx[0]}")

    # 配置
    print("\n当前配置:")
    configs = ['journal_mode', 'synchronous', 'cache_size', 'temp_store']
    for config in configs:
        cursor.execute(f"PRAGMA {config}")
        value = cursor.fetchone()[0]
        print(f"  {config}: {value}")

    conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='数据库优化工具')
    parser.add_argument('--info', action='store_true', help='显示数据库信息')
    parser.add_argument('--optimize', action='store_true', help='优化数据库')

    args = parser.parse_args()

    if args.info:
        show_database_info()
    elif args.optimize or (not args.info and not args.optimize):
        optimize_database()

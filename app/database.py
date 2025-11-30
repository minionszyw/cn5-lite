"""
CN5-Lite 数据库管理

功能:
1. 数据库连接管理
2. 表结构初始化
3. 连接池管理
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional
from app.logger import get_logger

logger = get_logger(__name__)

# 全局数据库连接
_db_connection: Optional[sqlite3.Connection] = None


def get_db_path() -> str:
    """
    获取数据库文件路径

    Returns:
        数据库文件路径
    """
    # 从环境变量获取，默认使用data/cn5lite.db
    db_path = os.getenv("DATABASE_PATH", "data/cn5lite.db")

    # 确保目录存在
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    return db_path


def get_db() -> sqlite3.Connection:
    """
    获取数据库连接（单例模式）

    Returns:
        数据库连接
    """
    global _db_connection

    if _db_connection is None:
        db_path = get_db_path()
        _db_connection = sqlite3.connect(db_path, check_same_thread=False)
        _db_connection.row_factory = sqlite3.Row

        logger.info(f"数据库连接已建立", path=db_path)

        # 初始化表结构
        _init_tables(_db_connection)

    return _db_connection


def _init_tables(conn: sqlite3.Connection):
    """
    初始化数据库表结构

    Args:
        conn: 数据库连接
    """
    # strategies表
    conn.execute("""
    CREATE TABLE IF NOT EXISTS strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        params TEXT,
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        deleted_at TEXT
    )
    """)

    # backtest_results表
    conn.execute("""
    CREATE TABLE IF NOT EXISTS backtest_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER NOT NULL,
        annual_return REAL,
        max_drawdown REAL,
        sharpe_ratio REAL,
        win_rate REAL,
        total_trades INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (strategy_id) REFERENCES strategies (id)
    )
    """)

    # trades表
    conn.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        action TEXT NOT NULL,
        price REAL NOT NULL,
        volume INTEGER NOT NULL,
        status TEXT NOT NULL,
        date TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (strategy_id) REFERENCES strategies (id)
    )
    """)

    # shadow_accounts表
    conn.execute("""
    CREATE TABLE IF NOT EXISTS shadow_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER NOT NULL,
        initial_cash REAL NOT NULL,
        current_cash REAL NOT NULL,
        observation_days INTEGER DEFAULT 0,
        score REAL DEFAULT 0.0,
        status TEXT DEFAULT 'observing',
        created_at TEXT NOT NULL,
        promoted_at TEXT,
        FOREIGN KEY (strategy_id) REFERENCES strategies (id)
    )
    """)

    conn.commit()

    logger.info("数据库表结构初始化完成")


def close_db():
    """关闭数据库连接"""
    global _db_connection

    if _db_connection:
        _db_connection.close()
        _db_connection = None
        logger.info("数据库连接已关闭")


def reset_db():
    """
    重置数据库（测试用）

    ⚠️ 仅用于测试环境
    """
    global _db_connection

    # 关闭现有连接
    close_db()

    # 删除数据库文件
    db_path = get_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.warning(f"数据库已删除", path=db_path)

    # 重新初始化
    _db_connection = None
    get_db()

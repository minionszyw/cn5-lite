-- CN5-Lite 数据库初始化脚本
-- 版本: 1.0
-- 日期: 2025-11-29

-- ===================
-- 1. 策略表
-- ===================
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code TEXT NOT NULL,
    params JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'draft',  -- draft/testing/shadow/live
    annual_return DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE strategies IS '策略表 - 存储AI生成的策略代码和元数据';
COMMENT ON COLUMN strategies.status IS '策略状态: draft-草稿, testing-测试中, shadow-影子账户, live-模拟盘';

-- ===================
-- 2. 回测结果表
-- ===================
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    strategy_id INT REFERENCES strategies(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_cash DECIMAL(15,2) DEFAULT 100000,
    final_value DECIMAL(15,2),
    annual_return DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    win_rate DECIMAL(8,4),
    total_trades INT,
    equity_curve JSONB,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE backtest_results IS '回测结果表 - 存储策略回测的完整指标';

-- ===================
-- 3. 影子账户表
-- ===================
CREATE TABLE shadow_accounts (
    id SERIAL PRIMARY KEY,
    strategy_id INT REFERENCES strategies(id) ON DELETE CASCADE,
    initial_cash DECIMAL(15,2) DEFAULT 100000,
    current_cash DECIMAL(15,2),
    total_value DECIMAL(15,2),
    status VARCHAR(20) DEFAULT 'running',  -- running/paused/promoted/failed
    observation_days INT DEFAULT 7,
    weighted_score DECIMAL(8,4),
    ranking INT,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE shadow_accounts IS '影子账户表 - 历史数据回放评估策略表现';
COMMENT ON COLUMN shadow_accounts.weighted_score IS '加权评分: 年化30% + 夏普25% + 回撤20% + 波动15% + 胜率10%';

-- ===================
-- 4. 交易记录表
-- ===================
CREATE TABLE trades (
    id BIGSERIAL PRIMARY KEY,
    account_type VARCHAR(20) NOT NULL,  -- shadow/simulation/live
    account_id INT,
    strategy_id INT REFERENCES strategies(id),
    strategy_instance_id VARCHAR(50),  -- 区分策略不同参数运行实例
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,  -- buy/sell
    price DECIMAL(10,2) NOT NULL,
    volume INT NOT NULL,
    commission DECIMAL(10,2) DEFAULT 0,  -- 佣金记录
    tax DECIMAL(10,2) DEFAULT 0,  -- 印花税记录
    pnl DECIMAL(15,2),
    status VARCHAR(20) DEFAULT 'completed',  -- pending/completed/cancelled/failed
    trade_time TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE trades IS '交易记录表 - 所有交易明细(影子账户+模拟盘+实盘)';
COMMENT ON COLUMN trades.commission IS '佣金: 双向0.03%, 最低5元';
COMMENT ON COLUMN trades.tax IS '印花税: 卖出0.1%, 买入免税';

-- ===================
-- 5. K线数据表 (分区表)
-- ===================
CREATE TABLE klines (
    id BIGSERIAL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10,2) NOT NULL,
    high DECIMAL(10,2) NOT NULL,
    low DECIMAL(10,2) NOT NULL,
    close DECIMAL(10,2) NOT NULL,
    volume BIGINT NOT NULL,
    adjust_factor DECIMAL(10,6) DEFAULT 1.0,  -- 复权因子
    data_source VARCHAR(20),  -- akshare/baostock/efinance
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_kline UNIQUE(symbol, timestamp)
) PARTITION BY RANGE (timestamp);

COMMENT ON TABLE klines IS 'K线数据表 - 按时间分区提升查询性能';
COMMENT ON COLUMN klines.adjust_factor IS '复权因子: A股分红送股必需, 用于计算真实收益';

-- 创建分区 (2022-2026)
CREATE TABLE klines_2022 PARTITION OF klines
    FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');

CREATE TABLE klines_2023 PARTITION OF klines
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE klines_2024 PARTITION OF klines
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE klines_2025 PARTITION OF klines
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE klines_2026 PARTITION OF klines
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

-- ===================
-- 6. 风控日志表
-- ===================
CREATE TABLE risk_logs (
    id BIGSERIAL PRIMARY KEY,
    strategy_id INT REFERENCES strategies(id),
    account_type VARCHAR(20),
    account_id INT,
    rule_name VARCHAR(50) NOT NULL,  -- 触发的风控规则名称
    risk_level VARCHAR(20) NOT NULL,  -- low/medium/high/critical
    signal JSONB,  -- 原始交易信号
    rejection_reason TEXT,
    risk_score DECIMAL(8,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE risk_logs IS '风控日志表 - 记录所有风控检查和拦截';

-- ===================
-- 7. 系统日志表
-- ===================
CREATE TABLE system_logs (
    id BIGSERIAL PRIMARY KEY,
    module VARCHAR(50) NOT NULL,  -- multi_datasource/ai_generator/backtest_engine等
    level VARCHAR(20) NOT NULL,  -- debug/info/warning/error/critical
    message TEXT NOT NULL,
    extra_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE system_logs IS '系统日志表 - 全局日志记录';

-- ===================
-- 索引优化
-- ===================

-- 策略表索引
CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_strategies_created_at ON strategies(created_at DESC);

-- 回测结果索引
CREATE INDEX idx_backtest_strategy ON backtest_results(strategy_id);
CREATE INDEX idx_backtest_executed_at ON backtest_results(executed_at DESC);

-- 影子账户索引
CREATE INDEX idx_shadow_ranking ON shadow_accounts(ranking) WHERE ranking IS NOT NULL;
CREATE INDEX idx_shadow_status ON shadow_accounts(status);
CREATE INDEX idx_shadow_score ON shadow_accounts(weighted_score DESC) WHERE weighted_score IS NOT NULL;

-- 交易记录索引
CREATE INDEX idx_trades_account ON trades(account_type, account_id);
CREATE INDEX idx_trades_instance ON trades(strategy_instance_id);
CREATE INDEX idx_trades_strategy ON trades(strategy_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_time ON trades(trade_time DESC);

-- K线数据索引 (每个分区都会继承)
CREATE INDEX idx_klines_symbol ON klines(symbol, timestamp DESC);
CREATE INDEX idx_klines_timestamp ON klines(timestamp DESC);

-- 风控日志索引
CREATE INDEX idx_risk_logs_strategy ON risk_logs(strategy_id);
CREATE INDEX idx_risk_logs_level ON risk_logs(risk_level);
CREATE INDEX idx_risk_logs_created_at ON risk_logs(created_at DESC);

-- 系统日志索引
CREATE INDEX idx_system_logs_module ON system_logs(module);
CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_created_at ON system_logs(created_at DESC);

-- ===================
-- 初始化数据
-- ===================

-- 插入默认配置 (可选)
-- INSERT INTO strategies (name, code, params, status) VALUES
-- ('示例策略', '# 示例代码', '{"ma_period": 20}', 'draft');

-- ===================
-- 统计信息
-- ===================
DO $$
BEGIN
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'CN5-Lite 数据库初始化完成!';
    RAISE NOTICE '===========================================';
    RAISE NOTICE '已创建7张核心表:';
    RAISE NOTICE '  1. strategies - 策略表';
    RAISE NOTICE '  2. backtest_results - 回测结果表';
    RAISE NOTICE '  3. shadow_accounts - 影子账户表';
    RAISE NOTICE '  4. trades - 交易记录表';
    RAISE NOTICE '  5. klines - K线数据表 (分区: 2022-2026)';
    RAISE NOTICE '  6. risk_logs - 风控日志表';
    RAISE NOTICE '  7. system_logs - 系统日志表';
    RAISE NOTICE '===========================================';
    RAISE NOTICE '已创建5个K线分区表: klines_2022 ~ klines_2026';
    RAISE NOTICE '已创建优化索引: 20+个索引提升查询性能';
    RAISE NOTICE '===========================================';
END $$;

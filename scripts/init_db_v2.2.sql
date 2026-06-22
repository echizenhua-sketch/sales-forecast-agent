-- ============================================================
-- 产销预测智能工作台 - 数据库初始化脚本 v2.2
-- ============================================================
-- 数据库：MySQL 8.0+
-- 字符集：utf8mb4
-- 引擎：InnoDB
-- 版本：v2.2（已对齐技术评审报告 v2.2 和 PRD v2.1）
-- 创建日期：2026-06-21
--
-- v2.2 修正内容：
-- 1. ✅ SAR 字段修正为 5 个（sar_province, sar_dealer, sar_ecommerce, sar_ka, sar_expansion）
-- 2. ✅ 新增 10 个可满足/未满足明细字段（5个渠道 × 2）
-- 3. ✅ 新增 risk_score 字段用于风险排序
-- 4. ✅ 字段注释包含计算公式，提升可维护性
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS supply_demand_forecast
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE supply_demand_forecast;

-- ============================================================
-- 1. 用户表
-- ============================================================
DROP TABLE IF EXISTS sys_user;
CREATE TABLE sys_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希（bcrypt）',
    real_name VARCHAR(100) COMMENT '真实姓名',
    role VARCHAR(20) NOT NULL COMMENT '角色: ADMIN, MANAGER, PLANNER, ANALYST',
    department VARCHAR(100) COMMENT '部门',
    email VARCHAR(100) COMMENT '邮箱',
    status VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE, INACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_role (role),
    INDEX idx_department (department),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ============================================================
-- 2. 文件任务表
-- ============================================================
DROP TABLE IF EXISTS task_file;
CREATE TABLE task_file (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    task_name VARCHAR(200) COMMENT '任务名称',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '文件存储路径',
    file_size BIGINT NOT NULL COMMENT '文件大小（字节）',
    file_md5 VARCHAR(32) COMMENT '文件MD5校验值',
    upload_user_id BIGINT NOT NULL COMMENT '上传用户ID',
    status VARCHAR(20) NOT NULL COMMENT '状态: UPLOADING, PARSING, CALCULATING, SUCCESS, FAILED',
    error_message TEXT COMMENT '错误信息',
    progress INT DEFAULT 0 COMMENT '进度(0-100)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_user (upload_user_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at),
    FOREIGN KEY (upload_user_id) REFERENCES sys_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件任务表';

-- ============================================================
-- 3. SKU 预测明细表（v2.2 修正版 - 核心表）
-- ============================================================
DROP TABLE IF EXISTS sku_forecast_detail;
CREATE TABLE sku_forecast_detail (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    task_id BIGINT NOT NULL COMMENT '任务ID',
    month VARCHAR(7) NOT NULL COMMENT '月份（格式: 2024-05）',
    product_name VARCHAR(200) COMMENT '产品名称',
    sku_code VARCHAR(100) NOT NULL COMMENT 'SKU编码',
    material_code VARCHAR(100) COMMENT '物料编码',

    -- ============================================================
    -- 库存与排产
    -- ============================================================
    initial_inventory DECIMAL(18, 2) COMMENT '期初库存（4月30日库存）',
    production_plan DECIMAL(18, 2) COMMENT '排产计划（5月排产）',
    safety_stock DECIMAL(18, 2) COMMENT '安全库存',
    total_supply DECIMAL(18, 2) COMMENT '总供应 (= 期初库存 + 排产计划 - 安全库存预留)',

    -- ============================================================
    -- SAR 需求组成（v2.2 修正：5个独立渠道，与 PRD v2.1 保持一致）
    -- ============================================================
    sar_province DECIMAL(18, 2) COMMENT '省大区SAR',
    sar_dealer DECIMAL(18, 2) COMMENT '网络经销商SAR',
    sar_ecommerce DECIMAL(18, 2) COMMENT '电商直营SAR',
    sar_ka DECIMAL(18, 2) COMMENT 'KA部SAR',
    sar_expansion DECIMAL(18, 2) COMMENT '拓展部SAR',
    sar_total DECIMAL(18, 2) COMMENT '合计SAR (= 省大区 + 网络经销商 + 电商直营 + KA部 + 拓展部)',

    -- ============================================================
    -- 缺口与满足率
    -- ============================================================
    gap DECIMAL(18, 2) COMMENT 'SAR差异 (= 总供应 - 合计SAR)，负数表示缺货',
    service_level DECIMAL(5, 2) COMMENT '满足率(%) (= 可满足合计 / 合计SAR * 100)',

    -- ============================================================
    -- 可满足明细（v2.2 新增：5个渠道独立统计）
    -- ============================================================
    satisfied_province DECIMAL(18, 2) COMMENT '省大区可满足',
    satisfied_dealer DECIMAL(18, 2) COMMENT '网络经销商可满足',
    satisfied_ecommerce DECIMAL(18, 2) COMMENT '电商直营可满足',
    satisfied_ka DECIMAL(18, 2) COMMENT 'KA部可满足',
    satisfied_expansion DECIMAL(18, 2) COMMENT '拓展部可满足',
    satisfied_demand DECIMAL(18, 2) COMMENT '可满足合计 (= 5个渠道可满足之和)',

    -- ============================================================
    -- 未满足明细（v2.2 新增：5个渠道独立统计）
    -- ============================================================
    unsatisfied_province DECIMAL(18, 2) COMMENT '省大区未满足',
    unsatisfied_dealer DECIMAL(18, 2) COMMENT '网络经销商未满足',
    unsatisfied_ecommerce DECIMAL(18, 2) COMMENT '电商直营未满足',
    unsatisfied_ka DECIMAL(18, 2) COMMENT 'KA部未满足',
    unsatisfied_expansion DECIMAL(18, 2) COMMENT '拓展部未满足',
    unsatisfied_demand DECIMAL(18, 2) COMMENT '未满足合计 (= 5个渠道未满足之和)',

    -- ============================================================
    -- 风险标识（v2.2 修正：新增 risk_score 用于排序）
    -- ============================================================
    risk_level VARCHAR(20) COMMENT '风险等级: CRITICAL, HIGH, MEDIUM, NORMAL, OVERSTOCK, SUFFICIENT',
    risk_reason TEXT COMMENT '风险原因（详细说明）',
    risk_score DECIMAL(5, 2) COMMENT '风险评分（用于排序，数值越大风险越高，范围: 0-200）',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    -- ============================================================
    -- 索引设计（优化查询性能）
    -- ============================================================
    INDEX idx_task_month (task_id, month) COMMENT '按任务和月份查询',
    INDEX idx_sku (sku_code) COMMENT '按SKU编码查询',
    INDEX idx_risk (risk_level) COMMENT '按风险等级筛选',
    INDEX idx_task_risk (task_id, risk_level) COMMENT '按任务和风险等级筛选',
    INDEX idx_task_score (task_id, risk_score DESC) COMMENT '按任务和风险评分排序',
    FOREIGN KEY (task_id) REFERENCES task_file(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='SKU预测明细表（v2.2修正版）';

-- ============================================================
-- 4. 汇总结果表
-- ============================================================
DROP TABLE IF EXISTS task_summary;
CREATE TABLE task_summary (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    task_id BIGINT NOT NULL UNIQUE COMMENT '任务ID',
    month VARCHAR(7) NOT NULL COMMENT '月份（格式: 2024-05）',

    -- 汇总指标
    total_supply DECIMAL(18, 2) COMMENT '总供应',
    total_sar DECIMAL(18, 2) COMMENT '合计SAR',
    total_gap DECIMAL(18, 2) COMMENT '总缺口 (= 总供应 - 合计SAR)',
    service_level DECIMAL(5, 2) COMMENT '满足率(%)',
    target_service_level DECIMAL(5, 2) DEFAULT 98.00 COMMENT '目标满足率（默认98%）',
    inventory_turnover_days DECIMAL(5, 1) COMMENT '库存周转天数',

    -- 风险统计
    critical_risk_count INT DEFAULT 0 COMMENT '极高风险数量',
    high_risk_count INT DEFAULT 0 COMMENT '高风险数量',
    medium_risk_count INT DEFAULT 0 COMMENT '中风险数量',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_month (month),
    FOREIGN KEY (task_id) REFERENCES task_file(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='汇总结果表';

-- ============================================================
-- 5. AI 会话表
-- ============================================================
DROP TABLE IF EXISTS ai_conversation;
CREATE TABLE ai_conversation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    task_id BIGINT COMMENT '任务ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    session_id VARCHAR(64) NOT NULL COMMENT '会话ID（用于多轮对话）',
    question TEXT NOT NULL COMMENT '问题',
    answer TEXT NOT NULL COMMENT '回答',
    context JSON COMMENT '上下文信息（JSON格式）',
    reference JSON COMMENT '引用数据（JSON格式，如 {"table": "...", "sku": "...", "row": 1}）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_session (session_id),
    INDEX idx_task_user (task_id, user_id),
    INDEX idx_created (created_at),
    FOREIGN KEY (task_id) REFERENCES task_file(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES sys_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI会话表';

-- ============================================================
-- 6. 操作日志表
-- ============================================================
DROP TABLE IF EXISTS audit_log;
CREATE TABLE audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id BIGINT COMMENT '用户ID',
    username VARCHAR(50) COMMENT '用户名',
    operation VARCHAR(50) NOT NULL COMMENT '操作类型（LOGIN, UPLOAD, EXPORT, DELETE, AI_CHAT等）',
    resource_type VARCHAR(50) COMMENT '资源类型（TASK, FILE, REPORT等）',
    resource_id BIGINT COMMENT '资源ID',
    detail TEXT COMMENT '详细信息（JSON格式）',
    ip_address VARCHAR(45) COMMENT 'IP地址（支持IPv6）',
    user_agent VARCHAR(500) COMMENT 'User Agent',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_user_time (user_id, created_at),
    INDEX idx_operation (operation),
    INDEX idx_created (created_at),
    FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

-- ============================================================
-- 7. 导出记录表
-- ============================================================
DROP TABLE IF EXISTS export_record;
CREATE TABLE export_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    task_id BIGINT COMMENT '任务ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    export_type VARCHAR(20) NOT NULL COMMENT '导出类型（SUMMARY, SKU_DETAIL, AI_CONVERSATION等）',
    export_format VARCHAR(10) NOT NULL COMMENT '导出格式（XLSX, CSV, PDF）',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '文件路径',
    file_size BIGINT COMMENT '文件大小（字节）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_task (task_id),
    INDEX idx_user (user_id),
    INDEX idx_created (created_at),
    FOREIGN KEY (task_id) REFERENCES task_file(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES sys_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='导出记录表';

-- ============================================================
-- 8. 系统配置表（可选）
-- ============================================================
DROP TABLE IF EXISTS system_config;
CREATE TABLE system_config (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    config_key VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    config_type VARCHAR(20) COMMENT '配置类型（STRING, NUMBER, JSON等）',
    description VARCHAR(500) COMMENT '配置描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- ============================================================
-- 初始化数据
-- ============================================================

-- 插入管理员账号（密码：admin123，需要在应用层使用 bcrypt 哈希）
INSERT INTO sys_user (username, password_hash, real_name, role, email, status) VALUES
('admin', '$2b$12$placeholder_hash_replace_with_real_hash', '系统管理员', 'ADMIN', 'admin@example.com', 'ACTIVE');

-- 插入系统配置（风险等级阈值）
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('risk.critical.gap_ratio', '-0.30', 'NUMBER', '极高风险缺口比例阈值'),
('risk.critical.gap_absolute', '10000', 'NUMBER', '极高风险缺口绝对值阈值'),
('risk.high.gap_ratio_min', '-0.30', 'NUMBER', '高风险缺口比例最小值'),
('risk.high.gap_ratio_max', '-0.15', 'NUMBER', '高风险缺口比例最大值'),
('risk.high.gap_absolute', '5000', 'NUMBER', '高风险缺口绝对值阈值'),
('risk.medium.gap_ratio_min', '-0.15', 'NUMBER', '中风险缺口比例最小值'),
('risk.medium.gap_ratio_max', '-0.05', 'NUMBER', '中风险缺口比例最大值'),
('service_level.target', '98.00', 'NUMBER', '目标满足率（%）'),
('file.max_size', '52428800', 'NUMBER', '文件上传大小上限（字节，50MB）'),
('ai.daily_limit', '100', 'NUMBER', 'AI 每日调用限额');

-- ============================================================
-- 数据验证视图（用于检查数据一致性）
-- ============================================================
CREATE OR REPLACE VIEW v_data_validation AS
SELECT
    id,
    sku_code,
    -- 验证 SAR 合计
    (sar_province + sar_dealer + sar_ecommerce + sar_ka + sar_expansion) AS calculated_sar_total,
    sar_total AS actual_sar_total,
    ABS((sar_province + sar_dealer + sar_ecommerce + sar_ka + sar_expansion) - sar_total) AS sar_diff,

    -- 验证缺口计算
    (total_supply - sar_total) AS calculated_gap,
    gap AS actual_gap,
    ABS((total_supply - sar_total) - gap) AS gap_diff,

    -- 验证可满足合计
    (satisfied_province + satisfied_dealer + satisfied_ecommerce + satisfied_ka + satisfied_expansion) AS calculated_satisfied_demand,
    satisfied_demand AS actual_satisfied_demand,
    ABS((satisfied_province + satisfied_dealer + satisfied_ecommerce + satisfied_ka + satisfied_expansion) - satisfied_demand) AS satisfied_diff,

    -- 验证未满足合计
    (unsatisfied_province + unsatisfied_dealer + unsatisfied_ecommerce + unsatisfied_ka + unsatisfied_expansion) AS calculated_unsatisfied_demand,
    unsatisfied_demand AS actual_unsatisfied_demand,
    ABS((unsatisfied_province + unsatisfied_dealer + unsatisfied_ecommerce + unsatisfied_ka + unsatisfied_expansion) - unsatisfied_demand) AS unsatisfied_diff,

    -- 验证可满足 + 未满足 = 合计SAR
    (satisfied_demand + unsatisfied_demand) AS total_demand_check,
    sar_total AS expected_sar_total,
    ABS((satisfied_demand + unsatisfied_demand) - sar_total) AS total_demand_diff
FROM sku_forecast_detail;

-- ============================================================
-- 验证脚本（执行后检查结果）
-- ============================================================

-- 验证表结构
SELECT
    TABLE_NAME,
    TABLE_COMMENT,
    TABLE_ROWS
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'supply_demand_forecast'
ORDER BY TABLE_NAME;

-- 验证 SKU 明细表字段数量（应为 37 个核心字段）
SELECT
    COUNT(*) AS total_columns,
    SUM(CASE WHEN COLUMN_NAME LIKE 'sar_%' THEN 1 ELSE 0 END) AS sar_columns,
    SUM(CASE WHEN COLUMN_NAME LIKE 'satisfied_%' THEN 1 ELSE 0 END) AS satisfied_columns,
    SUM(CASE WHEN COLUMN_NAME LIKE 'unsatisfied_%' THEN 1 ELSE 0 END) AS unsatisfied_columns
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'supply_demand_forecast'
  AND TABLE_NAME = 'sku_forecast_detail';

-- 预期结果：
-- sar_columns = 6 (province, dealer, ecommerce, ka, expansion, total)
-- satisfied_columns = 6 (5个渠道 + demand)
-- unsatisfied_columns = 6 (5个渠道 + demand)

-- 验证字段命名（检查是否存在旧字段名）
SELECT COLUMN_NAME, COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'supply_demand_forecast'
  AND TABLE_NAME = 'sku_forecast_detail'
  AND (COLUMN_NAME LIKE 'sar_%' OR COLUMN_NAME LIKE '%satisfied%' OR COLUMN_NAME = 'risk_score')
ORDER BY ORDINAL_POSITION;

-- ============================================================
-- 完成提示
-- ============================================================
SELECT
    '数据库初始化完成 v2.2' AS message,
    COUNT(DISTINCT TABLE_NAME) AS table_count,
    '已对齐技术评审报告 v2.2 和 PRD v2.1' AS status
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'supply_demand_forecast';

-- ============================================================
-- 使用说明
-- ============================================================
-- 1. 执行本脚本前，请确保 MySQL 版本 >= 8.0
-- 2. 管理员密码需要在应用层使用 bcrypt 生成真实哈希值
-- 3. 系统配置的阈值可根据业务需求调整
-- 4. 执行完成后，使用验证脚本检查表结构和字段
-- 5. 参考文档：技术评审报告 v2.2 第 3.1 节
-- ============================================================

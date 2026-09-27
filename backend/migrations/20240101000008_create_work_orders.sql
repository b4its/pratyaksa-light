-- Migration: Create work_orders table (persistensi Work Order dari Analisa/Telegram)

CREATE TABLE IF NOT EXISTS work_orders (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seq               BIGSERIAL UNIQUE,
    asset_code        VARCHAR(80)  NOT NULL,
    equipment_type    VARCHAR(120) NOT NULL DEFAULT 'Heavy Equipment',
    status_unit       VARCHAR(20)  NOT NULL DEFAULT 'CRITICAL'
                          CHECK (status_unit IN ('WARNING', 'CRITICAL', 'RUSAK')),
    priority          VARCHAR(10)  NOT NULL DEFAULT 'HIGH'
                          CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW')),
    component         VARCHAR(120) NOT NULL DEFAULT 'Komponen Utama',
    part_no           VARCHAR(80),
    rul_hours         INTEGER      NOT NULL DEFAULT 0,
    est_cost          BIGINT       NOT NULL DEFAULT 0,
    scheduled_at      TIMESTAMPTZ,
    est_completion_at TIMESTAMPTZ,
    technician        VARCHAR(120),
    notes             TEXT,
    feedback          VARCHAR(20)
                          CHECK (feedback IS NULL OR feedback IN ('as_predicted', 'worse', 'better', 'false_alarm')),
    wo_status         VARCHAR(20)  NOT NULL DEFAULT 'OPEN'
                          CHECK (wo_status IN ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_work_orders_asset   ON work_orders(asset_code);
CREATE INDEX IF NOT EXISTS idx_work_orders_status  ON work_orders(wo_status);
CREATE INDEX IF NOT EXISTS idx_work_orders_created ON work_orders(created_at DESC);

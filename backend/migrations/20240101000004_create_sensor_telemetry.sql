-- Migration: Sensor Telemetry (33 kolom)
-- Sumber data:
--   1. ECM / VIMS / KOMTRAX  (on-board telemetry)
--   2. FMS / Dispatch         (payload, operator, component type)
--   3. CMMS / Asset Mgmt      (design life, age, remanufactured)
--   4. LIMS / Lab Oli         (kandungan logam & kontaminasi)
--   5. Engineer Generated     (delta temp, status label, RUL)

CREATE TABLE IF NOT EXISTS sensor_telemetry (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identitas & Waktu
    ts                       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    unit_id                  UUID NOT NULL REFERENCES unit_tambang(id) ON DELETE CASCADE,

    -- FMS / Master data
    component_type           VARCHAR(50)  NOT NULL DEFAULT 'Heavy Equipment',
    operator_id              VARCHAR(50),
    payload_tonnage          DOUBLE PRECISION,

    -- CMMS / Masa hidup komponen
    hour_meter_actual        DOUBLE PRECISION,
    design_life_hm           DOUBLE PRECISION,
    component_age_hm         DOUBLE PRECISION,
    is_remanufactured        BOOLEAN NOT NULL DEFAULT FALSE,

    -- Lingkungan
    ambient_temp_c           DOUBLE PRECISION,

    -- Operasional & sensor fisik (ECM/VIMS)
    idle_time_ratio          DOUBLE PRECISION,
    eng_coolant_temp_c       DOUBLE PRECISION,
    eng_oil_press_psi        DOUBLE PRECISION,
    eng_rpm                  DOUBLE PRECISION,
    eng_load_pct             DOUBLE PRECISION,
    hyd_pump_press_psi       DOUBLE PRECISION,
    hyd_oil_temp_c           DOUBLE PRECISION,
    trans_oil_temp_c         DOUBLE PRECISION,
    torque_converter_temp_c  DOUBLE PRECISION,
    final_drive_temp_c       DOUBLE PRECISION,
    brake_cooling_temp_c     DOUBLE PRECISION,
    battery_voltage          DOUBLE PRECISION,
    fault_code_severity      INTEGER NOT NULL DEFAULT 0,

    -- LIMS / Lab analisis oli
    lab_fe_ppm               DOUBLE PRECISION,
    lab_cu_ppm               DOUBLE PRECISION,
    lab_al_ppm               DOUBLE PRECISION,
    lab_si_ppm               DOUBLE PRECISION,
    lab_viscosity_100c       DOUBLE PRECISION,
    lab_water_content_pct    DOUBLE PRECISION,
    lab_soot_pct             DOUBLE PRECISION,

    -- Engineer generated
    delta_eng_temp           DOUBLE PRECISION,
    status_label             VARCHAR(20),
    rul_hours                DOUBLE PRECISION,

    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_unit_ts ON sensor_telemetry(unit_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_status ON sensor_telemetry(status_label);

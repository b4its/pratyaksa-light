-- Migration: Create unit_tambang table

CREATE TABLE IF NOT EXISTS unit_tambang (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code                VARCHAR(50) NOT NULL UNIQUE,
    jenis_alat_berat_id UUID NOT NULL REFERENCES jenis_alat_berat(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'SEHAT'
                            CHECK (status IN ('SEHAT', 'WARNING', 'CRITICAL', 'RUSAK')),
    health              INTEGER NOT NULL DEFAULT 100
                            CHECK (health >= 0 AND health <= 100),
    maintenance         VARCHAR(200) NOT NULL DEFAULT '-',
    savings             BIGINT NOT NULL DEFAULT 0,
    img_url             TEXT,
    model3d_url         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_unit_tambang_code ON unit_tambang(code);
CREATE INDEX IF NOT EXISTS idx_unit_tambang_status ON unit_tambang(status);
CREATE INDEX IF NOT EXISTS idx_unit_tambang_jenis ON unit_tambang(jenis_alat_berat_id);

-- Seed sample units (requires jenis_alat_berat to exist)
INSERT INTO unit_tambang (id, code, jenis_alat_berat_id, status, health, maintenance, savings, img_url, model3d_url)
SELECT
    gen_random_uuid(),
    'EXC-320-01',
    j.id,
    'SEHAT',
    96,
    '120 Jam Lagi',
    2456,
    'https://placehold.co/400x250?text=Excavator',
    'https://modelviewer.dev/shared-assets/models/RobotExpressive.glb'
FROM jenis_alat_berat j WHERE j.nama = 'Caterpillar Excavator 320'
ON CONFLICT (code) DO NOTHING;

INSERT INTO unit_tambang (id, code, jenis_alat_berat_id, status, health, maintenance, savings, img_url, model3d_url)
SELECT
    gen_random_uuid(),
    'DT-SCN-12',
    j.id,
    'WARNING',
    78,
    '35 Jam Lagi',
    820,
    'https://placehold.co/400x250?text=Dump+Truck',
    'https://modelviewer.dev/shared-assets/models/RobotExpressive.glb'
FROM jenis_alat_berat j WHERE j.nama = 'Scania Dump Truck P410'
ON CONFLICT (code) DO NOTHING;

INSERT INTO unit_tambang (id, code, jenis_alat_berat_id, status, health, maintenance, savings, img_url, model3d_url)
SELECT
    gen_random_uuid(),
    'DZ-KMTS-08',
    j.id,
    'CRITICAL',
    42,
    '8 Jam Lagi (Segera)',
    -4150,
    'https://placehold.co/400x250?text=Dozer',
    'https://modelviewer.dev/shared-assets/models/RobotExpressive.glb'
FROM jenis_alat_berat j WHERE j.nama = 'Komatsu Dozer D85A'
ON CONFLICT (code) DO NOTHING;

INSERT INTO unit_tambang (id, code, jenis_alat_berat_id, status, health, maintenance, savings, img_url, model3d_url)
SELECT
    gen_random_uuid(),
    'WL-SDLG-03',
    j.id,
    'RUSAK',
    15,
    'Sedang Perbaikan',
    -18000,
    'https://placehold.co/400x250?text=Loader',
    'https://modelviewer.dev/shared-assets/models/RobotExpressive.glb'
FROM jenis_alat_berat j WHERE j.nama = 'SDLG Wheel Loader LG956'
ON CONFLICT (code) DO NOTHING;

INSERT INTO unit_tambang (id, code, jenis_alat_berat_id, status, health, maintenance, savings, img_url, model3d_url)
SELECT
    gen_random_uuid(),
    'EXC-320-02',
    j.id,
    'SEHAT',
    92,
    '110 Jam Lagi',
    1200,
    'https://placehold.co/400x250?text=Excavator+2',
    'https://modelviewer.dev/shared-assets/models/RobotExpressive.glb'
FROM jenis_alat_berat j WHERE j.nama = 'Caterpillar Excavator 320'
ON CONFLICT (code) DO NOTHING;

INSERT INTO unit_tambang (id, code, jenis_alat_berat_id, status, health, maintenance, savings, img_url, model3d_url)
SELECT
    gen_random_uuid(),
    'DT-SCN-15',
    j.id,
    'SEHAT',
    88,
    '80 Jam Lagi',
    450,
    'https://placehold.co/400x250?text=Dump+Truck+2',
    'https://modelviewer.dev/shared-assets/models/RobotExpressive.glb'
FROM jenis_alat_berat j WHERE j.nama = 'Scania Dump Truck P410'
ON CONFLICT (code) DO NOTHING;

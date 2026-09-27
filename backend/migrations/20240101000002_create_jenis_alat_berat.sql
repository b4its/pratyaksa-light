-- Migration: Create jenis_alat_berat table

CREATE TABLE IF NOT EXISTS jenis_alat_berat (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nama        VARCHAR(200) NOT NULL,
    deskripsi   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jenis_alat_berat_nama ON jenis_alat_berat(nama);

-- Seed default jenis alat berat
INSERT INTO jenis_alat_berat (id, nama, deskripsi) VALUES
    (gen_random_uuid(), 'Caterpillar Excavator 320', 'Excavator hidrolik seri 320 dari Caterpillar, kapasitas bucket 1.2 m³'),
    (gen_random_uuid(), 'Scania Dump Truck P410', 'Dump truck bertenaga tinggi untuk transportasi material tambang'),
    (gen_random_uuid(), 'Komatsu Dozer D85A', 'Bulldozer seri D85A dari Komatsu untuk land clearing dan penggalian'),
    (gen_random_uuid(), 'SDLG Wheel Loader LG956', 'Wheel loader kapasitas 3 ton dari SDLG, cocok untuk loading material'),
    (gen_random_uuid(), 'Hitachi Zaxis 200', 'Excavator mid-size dari Hitachi dengan sistem hidraulik canggih')
ON CONFLICT DO NOTHING;

-- Migration: tambah koordinat (lat/lng) ke unit_tambang
-- Dipakai untuk Peta Sebaran Unit (dashboard) & Peta Sebaran Sensor (unit tambang)
-- berbasis data riil, bukan dummy.

ALTER TABLE unit_tambang ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION;
ALTER TABLE unit_tambang ADD COLUMN IF NOT EXISTS lng DOUBLE PRECISION;

-- Koordinat tersebar di area tambang Kutai, Kalimantan Timur (±2-3 km dari pusat)
UPDATE unit_tambang u SET lat = v.lat, lng = v.lng
FROM (VALUES
    ('EXC-320-01', -0.4980, 117.1480),
    ('DT-SCN-12',  -0.5010, 117.1605),
    ('DZ-KMTS-08', -0.5085, 117.1490),
    ('WL-SDLG-03', -0.5120, 117.1620),
    ('EXC-320-02', -0.4955, 117.1560),
    ('DT-SCN-15',  -0.5060, 117.1665),
    ('EXC-320-03', -0.5005, 117.1430),
    ('EXC-320-04', -0.5150, 117.1545),
    ('DT-SCN-20',  -0.4920, 117.1510),
    ('DT-SCN-22',  -0.5095, 117.1700),
    ('DZ-KMTS-09', -0.5040, 117.1390),
    ('DZ-KMTS-10', -0.5180, 117.1465),
    ('WL-SDLG-05', -0.4900, 117.1620),
    ('WL-SDLG-06', -0.5135, 117.1410),
    ('EXC-320-05', -0.4965, 117.1690),
    ('DT-SCN-25',  -0.5200, 117.1610),
    ('DZ-KMTS-11', -0.4945, 117.1430),
    ('WL-SDLG-07', -0.5160, 117.1700)
) AS v(code, lat, lng)
WHERE u.code = v.code AND (u.lat IS NULL OR u.lng IS NULL);

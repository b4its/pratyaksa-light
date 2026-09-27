-- Migration: Seed tambahan unit_tambang agar pagination & grid armada 3D ter-demo
-- (total unit menjadi >12 sehingga pagination muncul di tabel dan grid 3D)

INSERT INTO unit_tambang (id, code, jenis_alat_berat_id, status, health, maintenance, savings, img_url, model3d_url)
SELECT gen_random_uuid(), v.code, j.id, v.status, v.health, v.maintenance, v.savings,
       'https://placehold.co/400x250?text=' || replace(v.code, '-', '+'),
       'https://modelviewer.dev/shared-assets/models/RobotExpressive.glb'
FROM (
    VALUES
        ('EXC-320-03', 'Caterpillar Excavator 320', 'SEHAT',    94,  '105 Jam Lagi',        1850),
        ('EXC-320-04', 'Caterpillar Excavator 320', 'WARNING',  71,  '40 Jam Lagi',          620),
        ('DT-SCN-20',  'Scania Dump Truck P410',     'SEHAT',    90,  '95 Jam Lagi',          980),
        ('DT-SCN-22',  'Scania Dump Truck P410',     'CRITICAL', 38,  '6 Jam Lagi (Segera)', -3200),
        ('DZ-KMTS-09', 'Komatsu Dozer D85A',         'SEHAT',    85,  '70 Jam Lagi',          540),
        ('DZ-KMTS-10', 'Komatsu Dozer D85A',         'WARNING',  64,  '28 Jam Lagi',          310),
        ('WL-SDLG-05', 'SDLG Wheel Loader LG956',    'SEHAT',    91,  '88 Jam Lagi',          760),
        ('WL-SDLG-06', 'SDLG Wheel Loader LG956',    'RUSAK',    12,  'Menunggu Sparepart',  -21000),
        ('EXC-320-05', 'Caterpillar Excavator 320', 'SEHAT',    97,  '130 Jam Lagi',        2680),
        ('DT-SCN-25',  'Scania Dump Truck P410',     'WARNING',  76,  '33 Jam Lagi',          450),
        ('DZ-KMTS-11', 'Komatsu Dozer D85A',         'SEHAT',    89,  '92 Jam Lagi',          870),
        ('WL-SDLG-07', 'SDLG Wheel Loader LG956',    'CRITICAL', 45,  '10 Jam Lagi (Segera)', -2750)
) AS v(code, jenis_nama, status, health, maintenance, savings)
JOIN jenis_alat_berat j ON j.nama = v.jenis_nama
ON CONFLICT (code) DO NOTHING;

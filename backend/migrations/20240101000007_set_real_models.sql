-- Migration: ganti model 3D dummy (RobotExpressive) dengan model alat berat
-- realistis (CC0, disimpan di media frontend /media/models/*.glb).
-- Hanya unit yang masih memakai model dummy/null yang diubah; model upload
-- kustom (path /media/models/<timestamp>-...) tidak diganggu.

UPDATE unit_tambang u SET model3d_url = m.url
FROM (
    SELECT j.id AS jid,
        CASE
            WHEN j.nama ILIKE '%excav%'  THEN '/media/models/crane.glb'
            WHEN j.nama ILIKE '%dump%' OR j.nama ILIKE '%truck%' OR j.nama ILIKE '%haul%' THEN '/media/models/dump_truck.glb'
            WHEN j.nama ILIKE '%dozer%'  THEN '/media/models/bulldozer.glb'
            WHEN j.nama ILIKE '%loader%' THEN '/media/models/tractor.glb'
            ELSE '/media/models/bulldozer.glb'
        END AS url
    FROM jenis_alat_berat j
) m
WHERE u.jenis_alat_berat_id = m.jid
  AND (
    u.model3d_url IS NULL
    OR u.model3d_url ILIKE '%modelviewer.dev%'
    OR u.model3d_url ILIKE '%RobotExpressive%'
  );

# Hasil Pengujian

## Status: ✅ SEMUA BERHASIL

### Backend FastAPI (`backend/tests`, pytest)

`31 passed` — unit + integrasi terhadap PostgreSQL/MongoDB aktif.

| Kelompok | Jumlah | Cakupan |
|----------|:------:|---------|
| `test_security.py` | 5 | bcrypt roundtrip, verifikasi hash `$2y$` seed, JWT roundtrip/invalid |
| `test_simulator.py` | 6 | fleet/result/predict/features/workorder/explain deterministik |
| `test_health_analytics.py` | 6 | classify, risk band, telemetry/prediction/analysis derivation |
| `test_api_pratyaksa.py` | 6 | health, status/fleet, mode switch, validasi 37 fitur, proteksi auth |
| `test_api_crud.py` | 8 | auth, jenis/unit CRUD, telemetry, work-order lifecycle, analisa Mongo, dashboard, health overview |

### Telegram Bot (`telegram_bot_grpc/tests`, pytest)

`11 passed` — builder pesan + gRPC AlertService (state stub, tanpa jaringan).

| Kelompok | Jumlah | Cakupan |
|----------|:------:|---------|
| `test_messages.py` | 8 | esc/normalize_base, alert, fleet summary, status, unit detail, report, keyboard |
| `test_grpc_service.py` | 3 | SendAlert sukses, tanpa subscriber, HealthCheck hitung |

Uji asap server gRPC (`HealthCheck` lewat channel nyata) → **OK**.

### Frontend Svelte (`frontend`, svelte-check + build)

- `svelte-check`: **0 errors, 0 warnings**
- `pnpm build` (adapter-node): **sukses**

## Detail Pengujian Endpoint (contoh)

### Mode Simulasi

Server ML API tidak aktif → otomatis mode `simulasi`:

```json
{ "mode": "simulasi", "api_reachable": false, "fleet_count": 6 }
```

### Validasi 37 Fitur

```json
{
  "status": "error",
  "message": "features[] harus berisi tepat 37 angka, tapi menerima 3",
  "expected": 37,
  "received": 3
}
```

### Validasi Work Order

Component invalid → error daftar komponen; `risk_score` di luar `0.0–1.0` →
error range.

## Build Status

| Komponen | Check | Build |
|----------|-------|-------|
| `backend` (FastAPI) | ✅ pytest 31 passed | ✅ Dockerfile OK |
| `telegram_bot_grpc` (Python) | ✅ pytest 11 passed | ✅ Dockerfile OK |
| `frontend` (SvelteKit) | ✅ svelte-check 0/0 | ✅ adapter-node OK |

## Cara Menjalankan Pengujian

```bash
# Backend
cd backend && .venv/bin/python -m pytest -q

# Telegram bot
cd telegram_bot_grpc && .venv/bin/python -m pytest -q

# Frontend
cd frontend && pnpm check && pnpm build

# Integrasi Live API (butuh stack berjalan)
./test/test_live_api.sh
```

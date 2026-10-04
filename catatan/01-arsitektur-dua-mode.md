# Arsitektur Mode Simulasi

> **Catatan historis penghapusan live API.** Dokumen ini dahulu bernama
> "Arsitektur 2 Mode (Live / Simulasi)". Seluruh alur LIVE kini dihapus.

## Konsep

Pratyaksa berjalan sepenuhnya dalam **mode SIMULASI**: setiap data fleet,
prediksi, dan hasil analisa dihasilkan oleh engine **simulator deterministik**
internal (`backend/app/pratyaksa/simulator.py`). Tidak ada koneksi keluar ke
ML API eksternal maupun ML PostgreSQL.

```
┌───────────────────────────────────────────────┐
│         Simulator Internal (deterministik)      │
│     frand(seed) + time_bucket(interval)         │
│                                                  │
│   GET /pratyaksa/fleet  → data simulasi          │
│   GET /pratyaksa/result → prediksi simulasi      │
│   GET /pratyaksa/...    → semua dari simulator   │
└───────────────────────────────────────────────┘
```

## SharedPratyaksaState

State bersama (dibungkus `asyncio.Lock`, di-share via `app.state.pratyaksa`)
menyimpan:

| Field | Tipe | Deskripsi |
|-------|------|-----------|
| `mode` | `PratyaksaMode` | Selalu `SIMULASI` |
| `fleet_data` | `list[FleetAsset]` | Data fleet hasil simulasi |
| `health_status` | `Optional[HealthResponse]` | Health simulasi |
| `generated_at` | `Optional[float]` | Epoch detik snapshot fleet dibuat |

Implementasi: `backend/app/pratyaksa/state.py`. Fleet di-generate ulang setiap
`/pratyaksa/fleet|status|fleet/health` dibaca (simulator deterministik berbasis
time-bucket), sehingga data selalu segar.

## Yang Dihapus

Komponen integrasi live API berikut sudah tidak ada lagi di repo:

- `PratyaksaApiClient` (HTTP client ke ML API eksternal).
- `pratyaksa/polling.py` (loop polling asyncio ke ML API).
- `pratyaksa/sync.py` (sync ml-pratyaksa PostgreSQL → MongoDB).
- Route `/live/*` dan skema `schemas/live.py`.
- Mode switch / auto-detect & field `api_reachable`/`manual_mode`.

## Keuntungan

- **Zero dependency** — aplikasi tidak butuh ML API / jaringan eksternal.
- **Deterministik** — data simulasi konsisten (berbasis seed dari `asset_id`
  + `time_bucket`; helper `frand` identik dengan implementasi Rust).

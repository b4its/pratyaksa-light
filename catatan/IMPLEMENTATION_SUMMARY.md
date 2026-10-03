# Implementation Summary — Porting ke FastAPI + Svelte

## Tujuan

Mengubah seluruh tech stack PRATYAKSA dari **Rust (Actix-Web) + Nuxt 4**
menjadi **Python (FastAPI) + Svelte (SvelteKit)**, semuanya di folder
`py-pratyaksa`, dengan tetap mempertahankan kontrak API dan skema data.
Integrasi *live API* (polling ML eksternal) kemudian dihapus sehingga seluruh
data berasal dari simulator internal.

## Yang Dibuat

### 1. Backend FastAPI (`backend/`)
- 30+ endpoint REST di `/api/v1` + `/svc/*`.
- PostgreSQL via `asyncpg` + migration runner SQL idempoten.
- MongoDB via `pymongo` async dengan **batch consumer** (paritas desain Rust).
- JWT (python-jose) + bcrypt (hash lama `$2y$` tetap valid).
- PRATYAKSA: shared state + **simulator deterministik** (mode simulasi saja).
- Derivasi health-analytics (telemetry/prediction/operational/unit analysis).

### 2. Frontend SvelteKit (`frontend/`)
- Svelte 5 (runes) + Tailwind CSS v4 dengan design system port penuh.
- Store auth/theme/pratyaksa, API layer, Leaflet fleet-map, model resolver.
- Halaman: landing, login, register, dashboard, CRUD jenis/unit, analisa,
  work_order, redirect `/wo/create/[asset]`.

### 3. Telegram Bot Python (`telegram_bot_grpc/`)
- gRPC `AlertService` (grpcio.aio) — paritas penuh dengan versi tonic.
- Long-polling Telegram: `/start`, `/status`, `/detail`, `/pratyaksa|/ds`,
  `/unit <id>`, `/menu`, `/down` + inline keyboard.
- Kompilasi `.proto` otomatis, persisten subscriber, fleet cache in-memory.

### 4. Infra & Dokumentasi
- `docker-compose.yml` (6 service + profile), `.example.docker-compose.yml`.
- `nginx/nginx.conf`, `Dockerfile` per komponen, `.env.example`, `README.md`.
- `API_TESTING.md`, folder `catatan/`.

## Verifikasi

| Komponen | Perintah | Hasil |
|----------|----------|-------|
| Backend | `pytest` | 41 passed |
| Telegram bot | `pytest` | 13 passed |
| Frontend | `svelte-check` | 0 errors / 0 warnings |
| Frontend | `pnpm build` | sukses (adapter-node) |
| Compose | `docker compose config` | valid (6 service) |

## Catatan Kompatibilitas

- Skema DB identik → database lama tetap dapat dipakai.
- Kontrak API identik → frontend & bot kompatibel.
- Parameter simulasi (`frand`, `time_bucket`, seed) identik → hasil konsisten.

# ⛏️ PRATYAKSA — Mining Intelligence Platform (FastAPI + Svelte)

**Predictive Analytics & Traceability for Heavy Asset Condition Surveillance and Actualization**

Sistem AIoT Predictive dan Prescriptive Maintenance untuk Armada Alat Berat Tambang Batubara.

> Repositori ini adalah **porting tech stack** dari backend Rust (Actix-Web) + frontend Nuxt
> menjadi **backend Python (FastAPI)** + **frontend Svelte (SvelteKit)**. Kontrak API,
> model data, dan logika simulasi/derivasi dipertahankan 1:1.
>
> ⚠️ **Mode Simulasi saja.** Seluruh data dihasilkan oleh engine simulator internal
> (deterministik). Tidak ada koneksi ke ML API eksternal maupun ML PostgreSQL — semua
> integrasi *live API* telah dihapus.

---

| | |
|---|---|
| ⚙️ **Status** | MVP Fungsional |
| 🏆 **Kompetisi** | Kideco Innovation Challenge (KIC) 2026 |
| 👥 **Tim Oryphem** | Politeknik Negeri Samarinda |
| 🐍 **Backend** | FastAPI + asyncpg + async PyMongo |
| 🟠 **Frontend** | SvelteKit + Tailwind CSS v4 |

---

## Daftar Isi

- [Arsitektur](#arsitektur)
- [Mode Operasi](#mode-operasi)
- [Tech Stack](#tech-stack)
- [Struktur Proyek](#struktur-proyek)
- [API Endpoints](#api-endpoints)
- [Panduan Menjalankan](#panduan-menjalankan)
- [Development & Testing](#development--testing)
- [Environment Variables](#environment-variables)

---

## Arsitektur

```
┌───────────────────────────────────────────────────────────────────────┐
│                       PRATYAKSA — ARSITEKTUR                           │
│                                                                        │
│  Browser                                                               │
│     │                                                                  │
│     ▼  :80                                                             │
│  ┌──────────┐                                                          │
│  │  Nginx   │  ← satu pintu masuk (reverse proxy)                      │
│  └────┬─────┘                                                          │
│       │                                                                │
│  ┌────┴──────────────────┐                                             │
│  │  /api/*  &  /svc/*    │            /*                                  │
│  ▼                       ▼            ▼                                 │
│  ┌─────────────────────┐        ┌────────────────────────┐              │
│  │  FastAPI Backend    │        │  SvelteKit Frontend    │              │
│  │  (uvicorn :8080)    │        │  (adapter-node :3000)  │              │  ← port internal container
│  └──────┬──────────────┘        └────────────────────────┘              │
│         │                                                               │
│    ┌────┴──────────────────┐                                            │
│    ▼                       ▼                                            │
│  ┌──────────────┐  ┌──────────────┐                                     │
│  │  PostgreSQL  │  │   MongoDB    │                                     │
│  │  (Simulasi)  │  │   (Analisa)  │                                     │
│  └──────────────┘  └──────────────┘                                     │
└───────────────────────────────────────────────────────────────────────┘
```

Backend FastAPI menyajikan data **SIMULASI** yang dihasilkan engine internal
Python (derivasi deterministik), serta CRUD unit/jenis/work-order (PostgreSQL)
dan analisa kerusakan (MongoDB). Tidak ada polling ke ML API eksternal.

---

## Mode Operasi

| Mode | Sumber Data | Deskripsi |
|------|-------------|-----------|
| **SIMULASI** | Engine internal Python | Data deterministik (paritas `frand`/`time_bucket` dengan Rust) |

Pratyaksa berjalan **hanya** dalam mode simulasi. Endpoint `POST /pratyaksa/mode`
tetap ada untuk kompatibilitas kontrak API tetapi selalu mengembalikan
`mode: "simulasi"`.

---

## Tech Stack

### Backend
| Komponen | Teknologi |
|----------|-----------|
| Web framework | FastAPI + Uvicorn |
| Validasi / schema | Pydantic v2 |
| PostgreSQL driver | asyncpg (pool + migration runner SQL) |
| MongoDB driver | PyMongo (async API) dengan batch consumer |
| Auth | python-jose (JWT HS256) + bcrypt |
| Alert | gRPC (grpcio) ke service bot Telegram |

### Frontend
| Komponen | Teknologi |
|----------|-----------|
| Framework | SvelteKit 2 (Svelte 5 runes) |
| Styling | Tailwind CSS v4 (design token port) |
| Chart | Chart.js |
| Peta | Leaflet (Esri Topo + Hillshade) |
| 3D | Google `<model-viewer>` |
| Adapter | `@sveltejs/adapter-node` |

---

## Struktur Proyek

```
py-pratyaksa/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory + lifespan
│   │   ├── core/                   # config, errors, security, deps
│   │   ├── db/                     # postgres.py, mongo.py
│   │   ├── schemas/                # Pydantic models (per domain)
│   │   ├── services/               # health_analytics derivation, telegram gRPC
│   │   ├── pratyaksa/              # state, simulator (simulation-only)
│   │   └── api/routes/             # auth, dashboard, CRUD, analisa, pratyaksa, svc
│   ├── migrations/                 # SQL migrations (same as Rust)
│   ├── tests/                      # pytest (unit + integration)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api.ts              # API layer (paritas useApi)
│   │   │   ├── stores/             # auth, theme (runes)
│   │   │   ├── fleet-map.ts        # Leaflet builder
│   │   │   ├── models.ts           # jenis → .glb resolver
│   │   │   └── components/         # AppLogo, PanelSidebar
│   │   └── routes/                 # /, /account/*, /panel/*, /wo/create/[asset]
│   ├── static/                     # assets, media/models (.glb)
│   ├── package.json
│   └── Dockerfile
├── telegram_bot_grpc/              # Bot Telegram (Python gRPC + long-polling)
│   ├── bot/                        # config, messages, state, grpc_server, polling
│   ├── proto/alert.proto           # Definisi gRPC AlertService
│   ├── tests/                      # pytest (messages + gRPC service)
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/nginx.conf
├── catatan/                        # Dokumentasi proses pengembangan
├── docker-compose.yml
├── .example.docker-compose.yml
├── API_TESTING.md
└── .env.example
```

---

## API Endpoints

Semua endpoint di bawah prefix `/api/v1`. Endpoint service (`/svc/*`) juga
tersedia di bawah `/api/v1/svc/*` agar konsisten dengan base URL frontend.

| Method | Path | Auth | Deskripsi |
|--------|------|:----:|-----------|
| GET | `/health` | – | Health check |
| GET | `/fleet-summary` | – | Ringkasan armada (internal) |
| POST | `/auth/register` | – | Registrasi user |
| POST | `/auth/login` | – | Login → JWT |
| GET | `/auth/me` | ✔ | Info user saat ini |
| GET | `/dashboard` | ✔ | Statistik dashboard (simulasi) |
| GET/POST | `/jenis-alat-berat` | ✔ | List / create jenis alat berat |
| GET/PUT/DELETE | `/jenis-alat-berat/{id}` | ✔ | Detail / update / delete |
| GET/POST | `/unit-tambang` | ✔ | List / create unit tambang |
| GET/PUT/DELETE | `/unit-tambang/{id}` | ✔ | Detail / update / delete |
| GET | `/analisa/overview` | ✔ | Overview kesehatan armada (realtime) |
| GET | `/analisa/unit/{id}` | ✔ | Analisa detail satu unit |
| GET/POST | `/analisa` | ✔ | List / create analisa (MongoDB) |
| GET/PUT/DELETE | `/analisa/{id}` | ✔ | Detail / update / delete analisa |
| POST | `/telemetry` | ✔ | Ingestion telemetri (33 kolom) |
| GET | `/telemetry/unit/{id}` | ✔ | Riwayat telemetri unit |
| GET/POST | `/work-orders` | ✔ | List / create work order |
| GET/PUT | `/work-orders/{id}` | ✔ | Detail / update work order |
| GET | `/pratyaksa/status` | – | Status mode & fleet (simulasi) |
| GET | `/pratyaksa/fleet` | – | Data fleet (simulasi) |
| GET | `/pratyaksa/fleet/health` | – | Ringkasan health fleet |
| GET | `/pratyaksa/result/{asset_id}` | – | Hasil prediksi per asset |
| POST | `/pratyaksa/predict` | – | Prediksi (37 fitur) |
| POST | `/pratyaksa/workorder` | – | Generate WO dari simulator |
| GET | `/pratyaksa/features` | – | 37 nama fitur sensor |
| GET | `/pratyaksa/explain/{id}` | – | SHAP explanation |
| POST | `/pratyaksa/reload-models` | – | Reload model (simulasi) |
| POST | `/pratyaksa/mode` | – | Mode (selalu `simulasi`) |
| POST | `/svc/upload-model` | – | Upload model 3D (.glb/.gltf) — juga di `/api/v1/svc/upload-model` |
| POST | `/svc/send-alert` | – | Kirim alert ke bot Telegram (gRPC) — juga di `/api/v1/svc/send-alert` |

Dokumentasi interaktif: `http://localhost:8116/docs`.

Selengkapnya: lihat [`API_TESTING.md`](./API_TESTING.md) dan folder
[`catatan/`](./catatan/README.md).

---

## Telegram Bot

Service bot (`telegram_bot_grpc/`) berjalan sebagai kontainer terpisah dan
memiliki dua tanggung jawab:

1. **gRPC server** (port 50051) — menerima `SendAlert` dari backend
   (`POST /svc/send-alert`) lalu broadcast ke semua subscriber.
2. **Long-polling Telegram** — perintah interaktif:

| Perintah | Fungsi |
|----------|--------|
| `/start` | Daftar subscriber + menu inline |
| `/status` | Ringkasan armada |
| `/detail` | Laporan armada + detail analisa |
| `/pratyaksa` (`/ds`) | Status mode DS API |
| `/unit <asset_id>` | Detail prediksi satu unit |
| `/menu` | Tampilkan menu |
| `/down` | Berhenti berlangganan |

Jalankan: `docker compose --profile bot up -d`, atau `full` untuk seluruh stack.
Set `TELEGRAM_BOT_TOKEN` (dan opsional `TELEGRAM_CHAT_ID`).

---

## Panduan Menjalankan

### Cara 1 — Docker Compose (disarankan)

```bash
cp .env.example .env
# edit .env sesuai kebutuhan (opsional)
docker compose --profile full up -d --build
# akses: http://localhost:116  (APP_PORT)
```

Login default: **admin@pratyaksa.id / admin123**.

### Cara 2 — Manual (development)

**Backend:**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL="postgresql://pratyaksa:pratyaksa_secret@localhost:5468/pratyaksa_db"
export MONGODB_URL="mongodb://pratyaksa:pratyaksa_secret@localhost:27053"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8116
```

**Frontend:**
```bash
cd frontend
corepack enable
pnpm install
echo "PUBLIC_API_BASE=http://localhost:8116/api/v1" > .env
pnpm dev     # http://localhost:3036
```

---

## Development & Testing

**Backend tests** (unit + integrasi terhadap PostgreSQL/MongoDB aktif):
```bash
cd backend
.venv/bin/python -m pytest -q
```
> Test integrasi otomatis di-skip jika database tidak tersedia.

**Frontend type-check & build:**
```bash
cd frontend
pnpm check    # svelte-check
pnpm build    # production build (adapter-node)
```

---

## Environment Variables

Lihat `.env.example`. Ringkasan variabel penting:

| Variabel | Default | Keterangan |
|----------|---------|-----------|
| `DATABASE_URL` | — | Koneksi PostgreSQL (wajib) |
| `MONGODB_URL` | — | Koneksi MongoDB (wajib) |
| `MONGODB_NAME` | `pratyaksa` | Nama database MongoDB |
| `JWT_SECRET` | — | Secret JWT (ganti di produksi) |
| `PUBLIC_API_BASE` | `http://localhost:8116/api/v1` | Base URL API untuk frontend |
| `CORS_ORIGINS` | `*` | Origin CORS diizinkan (comma-separated) |

---

**Tim Oryphem** — Politeknik Negeri Samarinda · Kideco Innovation Challenge 2026

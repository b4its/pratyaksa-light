# ⛏️ PRATYAKSA — Mining Intelligence Platform (FastAPI + Svelte)

**Predictive Analytics & Traceability for Heavy Asset Condition Surveillance and Actualization**

Sistem AIoT Predictive dan Prescriptive Maintenance untuk Armada Alat Berat Tambang Batubara.

> Repositori ini adalah **porting tech stack** dari backend Rust (Actix-Web) + frontend Nuxt
> menjadi **backend Python (FastAPI)** + **frontend Svelte (SvelteKit)**. Kontrak API,
> model data, logika simulasi/derivasi, dan alur mode Live/Simulasi dipertahankan 1:1.

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
│  │  (uvicorn :8080)    │        │  (adapter-node :3000)  │              │
│  └──────┬──────────────┘        └────────────────────────┘              │
│         │                                                               │
│    ┌────┴──────────────────┐                                            │
│    ▼                       ▼                                            │
│  ┌──────────────┐  ┌──────────────┐   ┌──────────────────────────────┐  │
│  │  PostgreSQL  │  │   MongoDB    │   │  ML API (FastAPI :6000)      │  │
│  │  (Simulasi)  │  │   (Live)     │◄──│  XGBoost + LSTM MoE + SHAP   │  │
│  └──────────────┘  └──────────────┘   └──────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

Backend FastAPI menjembatani UI dan lapisan ML:

- **Mode SIMULASI** — data dari PostgreSQL lokal (derivasi deterministik).
- **Mode LIVE** — polling HTTP ke ML API → simpan ke MongoDB (batch, high-speed) → tampilkan di frontend.
- **Sync Background** — migrasi periodik data dari PostgreSQL `ml-pratyaksa` ke MongoDB lokal.

---

## Mode Operasi

| Mode | Sumber Data | Deskripsi |
|------|-------------|-----------|
| **SIMULASI** | PostgreSQL | Data deterministik dari engine internal Python (paritas `frand`/`time_bucket` dengan Rust) |
| **LIVE API** | ML API + MongoDB | Data real-time dari ML API eksternal, disimpan batch ke MongoDB |

Mode dipilih dari UI (`POST /api/v1/pratyaksa/mode`) dan dihormati oleh background polling loop
(manual mode lock).

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
| HTTP client | httpx (polling ML API) |
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
│   │   ├── pratyaksa/              # state, simulator, polling, sync
│   │   └── api/routes/             # auth, dashboard, CRUD, analisa, pratyaksa, live, svc
│   ├── migrations/                 # SQL migrations (same as Rust)
│   ├── tests/                      # pytest (unit + integration)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api.ts              # API layer (paritas useApi)
│   │   │   ├── stores/             # auth, theme, pratyaksa (runes)
│   │   │   ├── fleet-map.ts        # Leaflet builder
│   │   │   ├── models.ts           # jenis → .glb resolver
│   │   │   └── components/         # AppLogo, PanelSidebar, ModeSelector, ModeLockTabel
│   │   └── routes/                 # /, /account/*, /panel/*, /wo/create/[asset]
│   ├── static/                     # assets, media/models (.glb)
│   ├── package.json
│   └── Dockerfile
├── nginx/nginx.conf
├── docker-compose.yml
└── .env.example
```

---

## API Endpoints

Semua endpoint di bawah prefix `/api/v1` (kecuali `/svc/*`).

| Method | Path | Auth | Deskripsi |
|--------|------|:----:|-----------|
| GET | `/health` | – | Health check |
| GET | `/fleet-summary` | – | Ringkasan armada (internal) |
| POST | `/auth/register` | – | Registrasi user |
| POST | `/auth/login` | – | Login → JWT |
| GET | `/auth/me` | ✔ | Info user saat ini |
| GET | `/dashboard` | ✔ | Statistik dashboard (mode-aware) |
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
| GET | `/pratyaksa/status` | – | Status mode & reachability |
| GET | `/pratyaksa/fleet` | – | Data fleet (live/simulasi) |
| GET | `/pratyaksa/fleet/health` | – | Ringkasan health fleet |
| GET | `/pratyaksa/result/{asset_id}` | – | Hasil prediksi per asset |
| POST | `/pratyaksa/predict` | – | Prediksi (37 fitur) |
| POST | `/pratyaksa/workorder` | – | Generate WO dari ML |
| GET | `/pratyaksa/features` | – | 37 nama fitur sensor |
| GET | `/pratyaksa/explain/{id}` | – | SHAP explanation |
| POST | `/pratyaksa/reload-models` | – | Reload model ML |
| POST | `/pratyaksa/mode` | – | Ganti mode (live/simulasi/auto) |
| GET | `/live/predictions` | – | Prediksi tersimpan (MongoDB) |
| GET | `/live/predictions/{asset}/latest` | – | Prediksi terbaru per asset |
| GET | `/live/fleet` | – | Fleet snapshot tersimpan |
| GET | `/live/work-orders` | – | Work order tersimpan (live) |
| GET | `/live/stats` | – | Statistik data live |
| POST | `/svc/upload-model` | – | Upload model 3D (.glb/.gltf) |
| POST | `/svc/send-alert` | – | Kirim alert ke bot Telegram (gRPC) |

Dokumentasi interaktif: `http://localhost:8080/docs`.

---

## Panduan Menjalankan

### Cara 1 — Docker Compose (disarankan)

```bash
cp .env.example .env
# edit .env sesuai kebutuhan (opsional)
docker compose --profile full up -d --build
# akses: http://localhost
```

Login default: **admin@pratyaksa.id / admin123**.

### Cara 2 — Manual (development)

**Backend:**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL="postgresql://pratyaksa:pratyaksa_secret@localhost:5432/pratyaksa_db"
export MONGODB_URL="mongodb://pratyaksa:pratyaksa_secret@localhost:27017"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

**Frontend:**
```bash
cd frontend
corepack enable
pnpm install
echo "PUBLIC_API_BASE=http://localhost:8080/api/v1" > .env
pnpm dev     # http://localhost:3000
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
| `PRATYAKSA_API_URL` | `http://192.168.101.3:6000` | Endpoint ML API eksternal |
| `PRATYAKSA_POLL_INTERVAL` | `5` | Interval polling (detik) |
| `ML_POSTGRES_URL` | — | PostgreSQL `ml-pratyaksa` untuk sync |
| `ML_SYNC_INTERVAL` | `60` | Interval sync ML (detik) |
| `PUBLIC_API_BASE` | `http://localhost:8080/api/v1` | Base URL API untuk frontend |
| `CORS_ORIGINS` | `*` | Origin CORS diizinkan (comma-separated) |

---

**Tim Oryphem** — Politeknik Negeri Samarinda · Kideco Innovation Challenge 2026

# Struktur & Perubahan Kode Backend (FastAPI)

## Peta Modul

```
backend/app/
├── main.py                 # App factory + lifespan (DB, polling, sync)
├── core/
│   ├── config.py           # AppConfig (paritas config.rs)
│   ├── errors.py           # AppError + error envelope
│   ├── security.py         # bcrypt + JWT (python-jose)
│   └── deps.py             # Auth dependency (Bearer JWT)
├── db/
│   ├── postgres.py         # asyncpg pool + migration runner
│   └── mongo.py            # Async PyMongo + batch consumer
├── schemas/                # Pydantic v2 models per domain
├── services/
│   ├── health_analytics.py # Derivasi telemetry/prediction/operational/RUL/SHAP
│   └── telegram.py         # gRPC client ke telegram_bot_grpc
├── pratyaksa/
│   ├── state.py            # SharedPratyaksaState + PratyaksaApiClient
│   ├── simulator.py        # Generator deterministik (frand/time_bucket)
│   ├── polling.py          # Loop polling ML API
│   └── sync.py             # Sync ml-pratyaksa PostgreSQL → MongoDB
└── api/routes/             # auth, dashboard, CRUD, analisa, pratyaksa, live, svc
```

## Pemetaan dari Rust

| Komponen Rust | Padanan Python |
|---------------|----------------|
| `actix-web` App + `.configure(routes)` | `FastAPI` + `APIRouter` |
| `web::Data<PostgresDb>` | `app.state.pg` (asyncpg pool) |
| `sqlx::FromRow` | `asyncpg.Record` + serializer manual |
| `mongodb` driver | `pymongo.AsyncMongoClient` |
| `jsonwebtoken` | `python-jose` (HS256) |
| `bcrypt` crate | `bcrypt` (Python) — hash `$2y$` lama tetap valid |
| `tonic` gRPC bot | `grpcio` + `grpcio-tools` bot Python |
| `sqlx::migrate!` | Migration runner SQL idempoten (`PostgresDb.run_migrations`) |
| `tokio::spawn(start_polling)` | `asyncio.create_task(start_polling)` |

## Error Handling

`AppError` → response `{"status":"error","message":...}` via exception handler.
Framework `HTTPException` juga dibungkus ke envelope yang sama (lihat
`core/errors.py`).

## Migrasi Database

File SQL di `backend/migrations/` dijalankan berurutan dan dilacak pada tabel
`schema_migrations` (idempoten). Skema identik dengan proyek Rust.

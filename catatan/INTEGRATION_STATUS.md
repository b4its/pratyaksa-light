# Integration Status

Ringkasan status integrasi antar komponen pada stack FastAPI + Svelte.
Semua data Pratyaksa berasal dari **simulator internal** (mode simulasi).

| Integrasi | Status | Keterangan |
|-----------|:------:|------------|
| SvelteKit ↔ Backend FastAPI | ✅ | Semua endpoint `/api/v1` + `/svc` (+ alias `/api/v1/svc`) |
| Backend ↔ PostgreSQL | ✅ | asyncpg pool + migrations |
| Backend ↔ MongoDB | ✅ | Async PyMongo + batch consumer (analisa kerusakan) |
| Backend ↔ Simulator | ✅ | Engine deterministik internal (mode simulasi) |
| Backend ↔ Telegram Bot (gRPC) | ✅ | `/svc/send-alert` → gRPC `SendAlert` |
| Telegram Bot ↔ Telegram API | ✅ | long-polling getUpdates + sendMessage |
| Telegram Bot ↔ Backend | ✅ | `/fleet-summary`, `/pratyaksa/status`, `/pratyaksa/result` |
| Frontend ↔ Telegram (notif) | ✅ | via backend `/svc/send-alert` |
| Upload model 3D ↔ StaticFiles | ✅ | `/svc/upload-model` → `/media/models/*` (StaticFiles + nginx `/media/`) |
| Nginx ↔ Backend/Frontend | ✅ | `/api/*`, `/svc/*`, `/media/*` → backend; `/*` → frontend |

## Alur Data

```
Simulator Internal ──► Backend ──► Frontend
                         │
                         ├──► PostgreSQL (master data, telemetry, WO)
                         │
                         └──gRPC──► Telegram Bot ──► Telegram
```

## Mode

| Mode | Sumber |
|------|--------|
| SIMULASI (satu-satunya) | Simulator Python deterministik |

> Integrasi **live API** (polling ML API eksternal + sync ml-pratyaksa
> PostgreSQL → MongoDB + route `/live/*`) telah **dihapus**.

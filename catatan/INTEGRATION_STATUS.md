# Integration Status

Ringkasan status integrasi antar komponen pada stack FastAPI + Svelte.

| Integrasi | Status | Keterangan |
|-----------|:------:|------------|
| SvelteKit ↔ Backend FastAPI | ✅ | Semua endpoint `/api/v1` + `/svc` (+ alias `/api/v1/svc`) |
| Backend ↔ PostgreSQL | ✅ | asyncpg pool + migrations |
| Backend ↔ MongoDB | ✅ | Async PyMongo + batch consumer |
| Backend ↔ ML API (live) | ✅ | httpx polling + fallback simulasi |
| Backend ↔ ml-pratyaksa PG (sync) | ✅ | Task sync periodik |
| Backend ↔ Telegram Bot (gRPC) | ✅ | `/svc/send-alert` → gRPC `SendAlert` |
| Telegram Bot ↔ Telegram API | ✅ | long-polling getUpdates + sendMessage |
| Telegram Bot ↔ Backend | ✅ | `/fleet-summary`, `/pratyaksa/status`, `/pratyaksa/result` |
| Frontend ↔ Telegram (notif) | ✅ | via backend `/svc/send-alert` |
| Upload model 3D ↔ StaticFiles | ✅ | `/svc/upload-model` → `/media/models/*` (StaticFiles + nginx `/media/`) |
| Nginx ↔ Backend/Frontend | ✅ | `/api/*`, `/svc/*`, `/media/*` → backend; `/*` → frontend |

## Alur Data

```
ML API ──polling──► Backend ──batch──► MongoDB ──read──► Frontend
                      │
                      ├──► PostgreSQL (master data, telemetry, WO)
                      │
                      └──gRPC──► Telegram Bot ──► Telegram
```

## Mode

| Mode | Sumber | Fallback |
|------|--------|----------|
| SIMULASI | Simulator Python deterministik | – |
| LIVE | ML API eksternal | Otomatis ke SIMULASI bila unreachable |

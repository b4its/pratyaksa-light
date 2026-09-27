# Integrasi Telegram Bot (Python gRPC)

## Arsitektur Komunikasi

```
User → Telegram Bot (long-polling getUpdates, Python)
         │
         ├── /start     → Register subscriber + greeting + inline menu
         ├── /status    → GET /api/v1/fleet-summary (PostgreSQL)
         ├── /detail    → Fleet + analisa lengkap
         ├── /pratyaksa → GET /api/v1/pratyaksa/status (mode DS API) (alias /ds)
         ├── /unit <id> → GET /api/v1/pratyaksa/result/{asset_id} (RUL + Digital Twin + Last processed)
         ├── /menu      → Tampilkan menu inline
         └── /down      → Berhenti berlangganan (alias /berhenti, /stop)

Backend FastAPI → gRPC AlertService (grpcio client, app/services/telegram.py)
         │
         ├── SendAlert()   → Broadcast ke semua subscriber
         └── HealthCheck() → Cek fleet cache in-memory

Frontend Svelte → POST /svc/send-alert → backend → gRPC → Telegram
```

## Struktur Bot

```
telegram_bot_grpc/
├── main.py                 # Entrypoint: gRPC server + polling task
├── proto/alert.proto       # Definisi service (identik dengan versi Rust)
├── bot/
│   ├── config.py           # BotConfig dari env
│   ├── messages.py         # Builder pesan & keyboard (pure, mudah dites)
│   ├── state.py            # Subscriber + fleet cache + klien HTTP
│   ├── proto_loader.py     # Kompilasi .proto → stubs (grpc_tools)
│   ├── grpc_server.py      # AlertService (grpcio.aio)
│   └── polling.py          # Loop getUpdates + handler command
└── tests/                  # pytest (messages + gRPC service)
```

## Pemetaan dari Rust (tonic)

| Rust | Python |
|------|--------|
| `tonic::transport::Server` | `grpc.aio.server` |
| `#[tonic::async_trait] impl AlertService` | `AlertServiceServicer` |
| `reqwest` ke Telegram API | `httpx.AsyncClient` |
| `RwLock<HashSet<i64>>` | `asyncio.Lock` + `set` |
| `tokio::spawn(run_telegram_polling)` | `asyncio.create_task(run_polling)` |

## Contoh Output `/pratyaksa`

```
🤖 PRATYAKSA DS API Status

🟡 Mode       : simulasi
❌ Reachable : false
📦 Fleet Count : 6 unit
🩺 Health Check : 2s ago
📡 Fleet Poll   : 2s ago
```

## Alur Sinkronisasi

1. **Backend** polling ML API tiap 5 detik (`/health` → `/fleet`).
2. **SharedPratyaksaState** menyimpan mode + data fleet.
3. **Telegram Bot** query `/api/v1/pratyaksa/status` untuk cek mode.
4. **Frontend** polling `/api/v1/pratyaksa/fleet` tiap 5 detik.
5. Mode **LIVE** → data asli ML API; **SIMULASI** → data deterministik.

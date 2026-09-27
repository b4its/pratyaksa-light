# Arsitektur 2 Mode (Live / Simulasi)

## Konsep

Backend FastAPI memiliki **2 mode operasi** yang otomatis berganti berdasarkan
ketersediaan server ML API eksternal:

```
┌─────────────────────────────────────────────────┐
│         Background Polling Loop (asyncio)        │
│              Setiap 5 detik                      │
│                                                   │
│   GET /health → 200 OK?                          │
│        ├── Ya ──→ Mode = LIVE                    │
│        │           ├── GET /fleet → data asli     │
│        │           ├── simpan ke MongoDB (batch)  │
│        │           └── Proxy ke ML API            │
│        │                                           │
│        └── Tidak → Mode = SIMULASI               │
│                    ├── Generate data deterministik │
│                    └── Semua endpoint → simulasi   │
└─────────────────────────────────────────────────┘
```

## SharedPratyaksaState

State bersama (dibungkus `asyncio.Lock`, di-share via `app.state.pratyaksa`)
menyimpan:

| Field | Tipe | Deskripsi |
|-------|------|-----------|
| `mode` | `PratyaksaMode` | `LIVE` atau `SIMULASI` |
| `manual_mode` | `Optional[PratyaksaMode]` | Kunci mode manual oleh user |
| `fleet_data` | `list[FleetAsset]` | Data fleet (asli atau simulasi) |
| `health_status` | `Optional[HealthResponse]` | Health terakhir dari ML API |
| `last_health_check` | `Optional[float]` | Epoch detik health check |
| `last_fleet_poll` | `Optional[float]` | Epoch detik fleet poll |
| `api_reachable` | `bool` | Apakah ML API reachable |

Implementasi: `backend/app/pratyaksa/state.py`.

## Alur Mode Switching

1. **Startup** → default `SIMULASI` (safe mode); fleet di-seed data simulasi.
2. **Loop polling** (`backend/app/pratyaksa/polling.py`) → `GET /health`.
3. **Jika sukses** → `mode = LIVE`, fetch `/fleet`, simpan snapshot + result ke MongoDB.
4. **Jika gagal** → `mode = SIMULASI`, generate data deterministik.
5. **Manual mode lock** → jika user memilih mode via `POST /pratyaksa/mode`,
   polling menghormati pilihan tersebut (tidak menimpa).

## Batch Consumer MongoDB

Meniru desain Rust: producer (`store_prediction`, `store_fleet_snapshot`, dst.)
menaruh dokumen pada `asyncio.Queue`; task background mem-`insert_many` saat
batch penuh atau interval tercapai. Lihat `backend/app/db/mongo.py`.

## Keuntungan

- **Zero dependency** — aplikasi tetap jalan meski ML API mati.
- **Seamless** — frontend tidak perlu tahu mode aktif.
- **Deterministik** — data simulasi konsisten (berbasis seed dari `asset_id`
  + `time_bucket`; helper `frand` identik dengan implementasi Rust).

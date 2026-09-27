# Troubleshooting

## Umum

| Gejala | Penyebab | Solusi |
|--------|----------|--------|
| `401 Unauthorized` | Token tidak ada / kadaluarsa | Login ulang; pastikan header `Authorization: Bearer <token>` |
| `502 Bad Gateway` (mode live) | ML API eksternal down | Ganti ke mode `simulasi` via `/pratyaksa/mode` |
| `409 Conflict` | Duplikat nama jenis / kode unit | Gunakan nama/kode unik |
| `404 Not Found` | ID tidak ada (UUID/ObjectId salah) | Cek ID dari endpoint list |
| Koneksi DB gagal | Container `postgres`/`mongodb` belum siap | `docker compose ps`; tunggu `healthy` |

## Backend

### PostgreSQL — `gen_random_uuid()`
Postgres 13+ sudah menyediakan `gen_random_uuid()` tanpa ekstensi `pgcrypto`.
Image `postgres:16-alpine` aman.

### MongoDB batch consumer lambat menyimpan
Data live disimpan asinkron (batch). Cek `/live/stats` beberapa saat setelah
mode live aktif. Producer: `MongoDb.store_*`; flush saat batch penuh / interval.

### Verifikasi password gagal untuk user lama
Hash seed `$2y$05$...` (dibuat `htpasswd -nbB`) tetap valid karena memakai
library `bcrypt` langsung (bukan passlib). Jika memakai passlib + bcrypt 5.x,
akan error `password cannot be longer than 72 bytes` — makanya backend
memakai `bcrypt` langsung.

### Polling loop warning: "Health check gagal"
Normal jika ML API eksternal tidak reachable; backend otomatis ke mode simulasi.
Ubah target via `PRATYAKSA_API_URL`.

## Telegram Bot

| Gejala | Solusi |
|--------|--------|
| Bot tidak membalas | Set `TELEGRAM_BOT_TOKEN`; pastikan container `telegram-bot` up |
| Alert tidak terkirim (`failed_precondition: Belum ada subscriber`) | Kirim `/start` ke bot lebih dulu |
| `gRPC UNAVAILABLE` | Pastikan `TELEGRAM_GRPC_TARGET` benar & service bot aktif |
| gRPC stub error saat start | Dipastikan `grpcio-tools` terpasang (kompilasi `alert.proto`) |

## Frontend

### API tidak terpanggil (CORS)
Set `CORS_ORIGINS` di backend (default `*`). Untuk produksi, set origin spesifik.

### Peta Leaflet kosong
Tile Esri butuh koneksi internet. Pastikan jaringan keluar tersedia.

### `<model-viewer>` tidak render
Script dimuat dari CDN Google; butuh akses internet. Model `.glb` ada di
`static/media/models/`.

## Log Berguna

```bash
docker compose logs -f backend
docker compose logs -f telegram-bot | grep -i pratyaksa
docker compose logs -f frontend
```

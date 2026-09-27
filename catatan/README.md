# Catatan Proses Pengembangan PRATYAKSA (FastAPI + Svelte)

Dokumentasi proses porting, arsitektur, dan integrasi stack
**Backend FastAPI (Python)** dan **Frontend Svelte (SvelteKit)** dari
implementasi awal (Rust + Nuxt).

## Daftar Isi

| File | Isi |
|------|-----|
| [01-arsitektur-dua-mode](./01-arsitektur-dua-mode.md) | Arsitektur 2 mode (Live / Simulasi) |
| [02-perubahan-kode-backend](./02-perubahan-kode-backend.md) | Struktur & perubahan kode di `backend/` |
| [03-endpoint-api-lengkap](./03-endpoint-api-lengkap.md) | Dokumentasi endpoint API lengkap |
| [04-integrasi-telegram-bot](./04-integrasi-telegram-bot.md) | Sinkronisasi dengan Telegram Bot (Python gRPC) |
| [05-pengujian](./05-pengujian.md) | Hasil pengujian semua komponen |
| [06-troubleshooting](./06-troubleshooting.md) | Masalah yang ditemui dan solusinya |
| [07-integrasi-4-mode-dropdown](./07-integrasi-4-mode-dropdown.md) | Integrasi pemilih mode di UI |

## Ringkasan

PRATYAKSA adalah platform **Predictive Maintenance** untuk alat berat
pertambangan. Pada stack baru:

1. **Backend FastAPI** berfungsi sebagai **middleware proxy**:
   - **Polling** data dari ML API eksternal setiap 5 detik (background task asyncio).
   - **Otomatis switch** ke mode simulasi jika server ML tidak reachable.
   - **Proxy** semua endpoint untuk frontend Svelte.
   - Menyimpan data live ke MongoDB via batch consumer async.
2. **Frontend SvelteKit** menyajikan dashboard, CRUD, analitik, dan mode selector.
3. **Telegram Bot (Python)** menerima alert via gRPC dan menyajikan laporan
   real-time lewat long-polling Telegram.

> Kontrak API, skema data, dan perilaku mode Live/Simulasi **identik** dengan
> implementasi Rust awal, sehingga frontend dan integrasi tetap kompatibel.

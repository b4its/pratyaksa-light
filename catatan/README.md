# Catatan Proses Pengembangan PRATYAKSA (FastAPI + Svelte)

Dokumentasi proses porting, arsitektur, dan integrasi stack
**Backend FastAPI (Python)** dan **Frontend Svelte (SvelteKit)** dari
implementasi awal (Rust + Nuxt).

## Daftar Isi

| File | Isi |
|------|-----|
| [01-arsitektur-simulasi](./01-arsitektur-dua-mode.md) | Arsitektur mode simulasi |
| [02-perubahan-kode-backend](./02-perubahan-kode-backend.md) | Struktur & perubahan kode di `backend/` |
| [03-endpoint-api-lengkap](./03-endpoint-api-lengkap.md) | Dokumentasi endpoint API lengkap |
| [04-integrasi-telegram-bot](./04-integrasi-telegram-bot.md) | Sinkronisasi dengan Telegram Bot (Python gRPC) |
| [05-pengujian](./05-pengujian.md) | Hasil pengujian semua komponen |
| [06-troubleshooting](./06-troubleshooting.md) | Masalah yang ditemui dan solusinya |
| [07-integrasi-4-mode-dropdown](./07-integrasi-4-mode-dropdown.md) | Catatan penghapusan pemilih mode (historis) |

## Ringkasan

PRATYAKSA adalah platform **Predictive Maintenance** untuk alat berat
pertambangan. Pada stack baru:

1. **Backend FastAPI** menyajikan data **simulasi**:
   - Data fleet/prediksi dihasilkan engine **simulator deterministik** internal.
   - CRUD master data, telemetry, dan work order via PostgreSQL.
   - Laporan analisa kerusakan via MongoDB (batch consumer async).
2. **Frontend SvelteKit** menyajikan dashboard, CRUD, dan analitik.
3. **Telegram Bot (Python)** menerima alert via gRPC dan menyajikan laporan
   real-time lewat long-polling Telegram.

> ⚠️ **Mode simulasi saja.** Seluruh integrasi *live API* (polling ML API
> eksternal, sync ML PostgreSQL, dan data live di MongoDB) telah dihapus.
> Kontrak API dan skema data lain dipertahankan agar frontend & bot tetap
> kompatibel.

# Penghapusan Pemilih Mode (UI) — Catatan Historis

> **Dokumen historis.** Dahulu frontend punya komponen `ModeSelector.svelte` dan
> `ModeLockTabel.svelte` untuk memilih sumber data (Live API vs Simulasi) dan
> sub-mode analisa (4 opsi). Seluruh pemilih mode **telah dihapus** bersamaan
> dengan penghapusan integrasi live API.

## Yang Dihapus

| Komponen / State | Peran lama |
|------------------|------------|
| `ModeSelector.svelte` | Dropdown di header (branch + sub-mode) |
| `ModeLockTabel.svelte` | Tabel/kartu mode lengkap (varian `compact`) |
| `SourceMode` (store) | `live-silent` \| `live-telegram` \| `hit-endpoint-sendiri` \| `hit-endpoint-ml` |
| `pratyaksa.setMode()` | `POST /api/v1/pratyaksa/mode` |
| `PUBLIC_ML_TARGET_URL` / `PUBLIC_CUSTOM_TARGET_URL` | Target endpoint eksternal (di-bake saat build) |

## Kondisi Sekarang

- Backend berjalan **hanya** dalam mode `simulasi`; `POST /pratyaksa/mode`
  tetap ada untuk kompatibilitas kontrak API tetapi selalu mengembalikan
  `mode: "simulasi"`.
- Store `stores/pratyaksa.svelte.ts` hanya menyimpan `fleetData`, `status`
  (`mode`, `fleet_count`), dan `fleetHealth`; tidak ada state mode/target.
- Halaman panel tidak lagi menampilkan pemilih mode.
- Tombol **Test Telegram** tetap tersedia langsung di header halaman Analisa
  (memanggil `POST /svc/send-alert`).

## Alert Otomatis

Sebelumnya alert otomatis hanya aktif pada sub-mode `live-telegram`. Karena
pemilih sub-mode dihapus, alert otomatis (untuk unit `CRITICAL`/`WARNING`) kini
berjalan default di halaman Analisa selama halaman terbuka.

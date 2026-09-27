# Integrasi Mode Dropdown (UI)

`ModeSelector` di frontend menyajikan kombinasi **sumber data** × **mode analisa**,
selaras dengan implementasi Rust/Nuxt (4 sub-mode).

## Sumber Data (branch)

| ID | Label | Deskripsi |
|----|-------|-----------|
| `simulasi` | Live Simulasi | Data dari simulator internal (tanpa koneksi eksternal) |
| `live` | Live API | Data real-time dari ML API eksternal (192.168.101.3:6000) |

## Sub-mode / Mode Analisa

| ID (`sourceMode`) | Label | Deskripsi |
|-------------------|-------|-----------|
| `live-silent` | Live (tanpa Telegram) | Monitoring real-time tanpa notifikasi |
| `live-telegram` | Live + Kirim Telegram | Alert otomatis CRITICAL & WARNING ke Telegram |
| `hit-endpoint-sendiri` | Hit Endpoint Sendiri | Panggil endpoint kustom (`CUSTOM_TARGET_URL`) |
| `hit-endpoint-ml` | Hit Endpoint ML | Panggil endpoint ML terpisah (`ML_TARGET_URL`) |

Sub-mode disimpan sebagai state store (`pratyaksa.svelte.ts`, tipe `SourceMode`)
dan dipakai saat mengirim alert via `POST /svc/send-alert`.

## Komponen terkait

| Komponen | Peran |
|----------|-------|
| `ModeSelector.svelte` | Dropdown di header (branch + sub-mode + status footer) |
| `ModeLockTabel.svelte` | Tabel/kartu mode lengkap; varian `compact` menambah pill bar |
| `stores/pratyaksa.svelte.ts` | State mode, fleet, polling, `sourceMode`, target URL |

`ModeSelector`/`ModeLockTabel` menerima prop `showSubModes` (menampilkan panel
sub-mode) dan callback `ontesttelegram` (tombol **Test Telegram**).

## Alur Ganti Mode

1. User pilih branch → `POST /api/v1/pratyaksa/mode` `{mode}`.
2. Backend set `manual_mode` (mengunci pilihan).
3. Polling menghormati `manual_mode`.
4. Frontend `fetchAll()` me-refresh status + fleet + health.
5. User pilih sub-mode → `setSourceMode(<id>)` (state lokal, tanpa request).
6. Tombol Test Telegram → `POST /svc/send-alert` (payload uji).
7. Reset ke AUTO → `POST /pratyaksa/mode` `{reset:true}`.

Target endpoint eksternal dikonfigurasi via env `PUBLIC_ML_TARGET_URL` dan
`PUBLIC_CUSTOM_TARGET_URL` (di-bake saat build; lihat `frontend/Dockerfile`).

Implementasi frontend: `frontend/src/lib/components/ModeSelector.svelte` &
`frontend/src/lib/components/ModeLockTabel.svelte`.

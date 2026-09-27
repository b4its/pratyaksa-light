# Integrasi 4 Mode Dropdown (UI)

ModeSelector di frontend menyajikan kombinasi **sumber data** × **notifikasi**:

## Sumber Data

| ID | Label | Deskripsi |
|----|-------|-----------|
| `simulasi` | Live Simulasi | Data dari simulator internal (tanpa koneksi eksternal) |
| `live` | Live API | Data real-time dari ML API eksternal |

## Notifikasi (sub-mode)

| ID | Label | Deskripsi |
|----|-------|-----------|
| `silent` | Tanpa Telegram | Monitoring tanpa notifikasi |
| `telegram` | + Kirim Telegram | Alert otomatis ke Telegram |

## Pemetaan ke `sourceMode` (frontend)

| sumber × notifikasi | `sourceMode` |
|---------------------|--------------|
| simulasi × silent | `live-silent` |
| simulasi × telegram | `live-telegram` |
| live × silent | `live-silent` |
| live × telegram | `live-telegram` |

`sourceMode` disimpan sebagai state store (`pratyaksa.svelte.ts`) dan dipakai
saat mengirim alert via `POST /svc/send-alert`.

## Komponen terkait

| Komponen | Peran |
|----------|-------|
| `ModeSelector.svelte` | Dropdown di header (branch + sub-mode) |
| `ModeLockTabel.svelte` | Kartu ringkas 2 mode + detail di dashboard |
| `stores/pratyaksa.svelte.ts` | State mode, fleet, polling, `sourceMode` |

## Alur Ganti Mode

1. User pilih branch → `POST /api/v1/pratyaksa/mode` `{mode}`.
2. Backend set `manual_mode` (mengunci pilihan).
3. Polling menghormati `manual_mode`.
4. Frontend `fetchAll()` me-refresh status + fleet + health.
5. Reset ke AUTO → `POST /pratyaksa/mode` `{reset:true}`.

Implementasi frontend: `frontend/src/lib/components/ModeSelector.svelte`.

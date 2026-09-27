# Live API Integration Testing

Panduan menguji integrasi dengan ML API eksternal pada stack FastAPI + Svelte.

## Prasyarat

- Stack berjalan via Docker (`docker compose --profile full up -d`) **atau**
  backend manual (`uvicorn app.main:app`).
- ML API target dapat diakses (default `http://192.168.101.3:6000`) — opsional;
  jika tidak, sistem otomatis memakai mode simulasi.

## 1. Cek kesehatan langsung ke ML API

```bash
curl -s http://192.168.101.3:6000/health | jq '.'
```

## 2. Cek status backend

```bash
curl -s http://localhost:8080/api/v1/pratyaksa/status | jq '.data'
```

Contoh (mode simulasi karena ML API tidak reachable):

```json
{
  "mode": "simulasi",
  "manual_mode": null,
  "api_reachable": false,
  "fleet_count": 6,
  "last_health_check": "2s ago",
  "last_fleet_poll": "2s ago"
}
```

## 3. Data fleet (live atau simulasi)

```bash
curl -s http://localhost:8080/api/v1/pratyaksa/fleet | jq '.data.total'
curl -s http://localhost:8080/api/v1/pratyaksa/fleet/health | jq '.data'
```

## 4. Detail unit

```bash
for id in WA600-001 HD785-001 DT-001; do
  curl -s "http://localhost:8080/api/v1/pratyaksa/result/$id" | jq '.data.risk_level'
done
```

## 5. Ganti mode

```bash
# ke LIVE
curl -s -X POST http://localhost:8080/api/v1/pratyaksa/mode \
  -H "Content-Type: application/json" -d '{"mode":"live"}' | jq '.data'

# ke SIMULASI
curl -s -X POST http://localhost:8080/api/v1/pratyaksa/mode \
  -H "Content-Type: application/json" -d '{"mode":"simulasi"}' | jq '.data'

# reset ke AUTO
curl -s -X POST http://localhost:8080/api/v1/pratyaksa/mode \
  -H "Content-Type: application/json" -d '{"reset":true}' | jq '.data'
```

## 6. Data live tersimpan (MongoDB)

Aktifkan mode LIVE, tunggu beberapa detik, lalu:

```bash
curl -s http://localhost:8080/api/v1/live/stats | jq '.data'
curl -s http://localhost:8080/api/v1/live/predictions?limit=5 | jq '.total'
```

## 7. Skrip otomatis

```bash
./test/test_live_api.sh
```

## Monitoring Log

```bash
docker compose logs -f backend | grep -i pratyaksa
docker compose logs -f telegram-bot
```

## Troubleshooting

- Mode tetap `simulasi` → ML API tidak reachable. Cek `curl .../health`.
- Mode LIVE tapi `/live/stats` kosong → tunggu batch consumer flush (interval
  ~500ms–2s) atau periksa koneksi MongoDB.

Lihat juga: `catatan/06-troubleshooting.md`.

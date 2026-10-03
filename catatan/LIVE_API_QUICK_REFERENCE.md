# Live API Quick Reference

## Endpoint Inti

```bash
BACKEND=http://localhost:8116

# Status & mode
curl -s $BACKEND/api/v1/pratyaksa/status | jq '.data'
curl -s -X POST $BACKEND/api/v1/pratyaksa/mode \
  -H 'Content-Type: application/json' -d '{"mode":"live"}' | jq '.data'

# Fleet
curl -s $BACKEND/api/v1/pratyaksa/fleet | jq '.data.fleet | length'
curl -s $BACKEND/api/v1/pratyaksa/fleet/health | jq '.data'

# Unit
curl -s $BACKEND/api/v1/pratyaksa/result/WA600-001 | jq '.data'

# Fitur & predict (37 fitur)
curl -s $BACKEND/api/v1/pratyaksa/features | jq '.data.total'

# Live tersimpan
curl -s $BACKEND/api/v1/live/stats | jq '.data'
curl -s $BACKEND/api/v1/live/predictions | jq '.total'
```

## Environment

| Variabel | Default |
|----------|---------|
| `PRATYAKSA_API_URL` | `http://192.168.101.3:6000` |
| `PRATYAKSA_API_KEY` | `dev-key-pratyaksa` |
| `PRATYAKSA_POLL_INTERVAL` | `5` |
| `ML_POSTGRES_URL` | `postgresql://...@192.168.101.3:5432/pratyaksa` |
| `ML_SYNC_INTERVAL` | `60` |

## Perintah Cepat

```bash
# Semua service
docker compose --profile full up -d --build

# Log backend & bot
docker compose logs -f backend telegram-bot

# Uji end-to-end
./test/test_live_api.sh
```

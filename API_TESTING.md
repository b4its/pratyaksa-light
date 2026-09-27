# API Testing — Pratyaksa Backend (FastAPI)

Panduan lengkap menguji endpoint API backend **FastAPI** menggunakan `curl`.
Semua request lewat Nginx di `http://localhost/api/v1` (atau langsung
`http://localhost:8080/api/v1` saat menjalankan backend manual).

> Dokumentasi interaktif tersedia di `http://localhost:8080/docs` (Swagger UI).

---

## Prasyarat

Pastikan container sudah jalan:

```bash
docker compose --profile full up -d
docker compose ps
```

Semua service (`backend`, `frontend`, `telegram-bot`, `nginx`, `postgres`,
`mongodb`) harus berstatus **Up**.

---

## 1. Autentikasi

Semua endpoint kecuali `/health`, `/fleet-summary`, dan seluruh grup
`/pratyaksa/*` & `/live/*` memerlukan JWT token. Token berlaku **24 jam**.

### Login

```bash
curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@pratyaksa.id","password":"admin123"}' > login.json
```

Respons:

```json
{
  "status": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "9ab9afa5-a782-4e7d-b60d-04fc3e5cda7f",
      "name": "Budi Santoso",
      "email": "admin@pratyaksa.id",
      "role": "admin",
      "created_at": "2026-06-27T14:20:04.159489+00:00"
    }
  }
}
```

Pakai token di setiap request berikutnya:

```bash
-H "Authorization: Bearer $(jq -r '.data.token' login.json)"
```

### Register user baru

```bash
curl -s -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Engineer","email":"engineer@pratyaksa.id","password":"secret123"}'
```

### Info user saat ini

```bash
curl -s http://localhost/api/v1/auth/me \
  -H "Authorization: Bearer $(jq -r '.data.token' login.json)"
```

---

## 2. Analisa Kerusakan — POST `/analisa`

Menyimpan laporan analisa kesehatan unit ke **MongoDB**.

```bash
cat > analisa.json <<'EOF'
{
  "unit_tambang_id": "00000000-0000-0000-0000-000000000000",
  "unit_code": "EXC-320-01",
  "tipe_kerusakan": "Overheat Engine",
  "deskripsi": "Suhu coolant melampaui ambang batas aman.",
  "severity": "HIGH",
  "sensor_data": {
    "suhu_mesin": 112, "tekanan_oli": 4.8, "rpm": 1500,
    "fuel_level": 62, "vibration": 4.2, "jam_operasi": 8200
  },
  "rekomendasi": "Ganti coolant, inspeksi radiator.",
  "dilaporkan_oleh": "Engineer Siti"
}
EOF

curl -s -X POST http://localhost/api/v1/analisa \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(jq -r '.data.token' login.json)" \
  -d @analisa.json | jq '.'
```

**Aturan validasi:**
- `severity`: `LOW` | `MEDIUM` | `HIGH` | `CRITICAL`
- `tipe_kerusakan`: 2–200 karakter
- `deskripsi`: minimal 5 karakter
- `status_analisa` otomatis `OPEN` saat dibuat

---

## 3. Endpoint Analisa Lainnya

```bash
# List semua laporan (dengan filter)
curl -s "http://localhost/api/v1/analisa?severity=HIGH" \
  -H "Authorization: Bearer $(jq -r '.data.token' login.json)" | jq '.'

# Filter per unit / status
curl -s "http://localhost/api/v1/analisa?unit_tambang_id=<UUID>&status_analisa=OPEN" \
  -H "Authorization: Bearer $(jq -r '.data.token' login.json)" | jq '.'

# Get by ID (Mongo ObjectId string)
curl -s http://localhost/api/v1/analisa/<OBJECT_ID> \
  -H "Authorization: Bearer $(jq -r '.data.token' login.json)" | jq '.'

# Update status
curl -s -X PUT http://localhost/api/v1/analisa/<OBJECT_ID> \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(jq -r '.data.token' login.json)" \
  -d '{"status_analisa":"RESOLVED"}' | jq '.'

# Hapus
curl -s -X DELETE http://localhost/api/v1/analisa/<OBJECT_ID> \
  -H "Authorization: Bearer $(jq -r '.data.token' login.json)" | jq '.'
```

`status_analisa`: `OPEN` | `IN_PROGRESS` | `RESOLVED`.

---

## 4. Analitik Kesehatan Realtime

```bash
# Overview seluruh armada
curl -s http://localhost/api/v1/analisa/overview \
  -H "Authorization: Bearer $(jq -r '.data.token' login.json)" | jq '.data'

# Detail satu unit (ganti {id} dengan UUID unit dari /unit-tambang)
curl -s http://localhost/api/v1/analisa/unit/<UUID> \
  -H "Authorization: Bearer $(jq -r '.data.token' login.json)" | jq '.data'
```

---

## 5. Referensi Unit Tambang

```bash
# List unit
curl -s "http://localhost/api/v1/unit-tambang?per_page=5" \
  -H "Authorization: Bearer $(jq -r '.data.token' login.json)" | jq '.data.data'

# Jenis alat berat
curl -s http://localhost/api/v1/jenis-alat-berat \
  -H "Authorization: Bearer $(jq -r '.data.token' login.json)" | jq '.data.data'
```

---

## 6. PRATYAKSA ML / Mode (tanpa auth)

```bash
curl -s http://localhost/api/v1/pratyaksa/status | jq '.data'
curl -s http://localhost/api/v1/pratyaksa/fleet | jq '.data.total'
curl -s http://localhost/api/v1/pratyaksa/fleet/health | jq '.data'
curl -s -X POST http://localhost/api/v1/pratyaksa/mode \
  -H "Content-Type: application/json" -d '{"mode":"simulasi"}' | jq '.'
curl -s http://localhost/api/v1/pratyaksa/features | jq '.data.total'
```

---

## 7. Health Check (tanpa auth)

```bash
curl -s http://localhost/api/v1/health | jq '.'
# → {"status":"ok","service":"Pratyaksa Backend","version":"0.2.0"}

curl -s http://localhost/api/v1/fleet-summary | jq '.data'
```

---

## Troubleshooting

| Gejala | Penyebab | Solusi |
|--------|----------|--------|
| `401 Unauthorized` | Token tidak ada/kadaluarsa | Login ulang, cek header `Authorization` |
| `502 Bad Gateway` (mode live) | ML API eksternal down | Ganti ke mode `simulasi` |
| `409 Conflict` | Duplikat nama/kode unit | Gunakan nama/kode unik |
| Koneksi DB gagal | Container `postgres`/`mongodb` belum siap | `docker compose ps` lalu tunggu healthy |

Untuk pengujian Live API eksternal, jalankan `./test/test_live_api.sh`.

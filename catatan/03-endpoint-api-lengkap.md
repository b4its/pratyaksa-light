# Dokumentasi Endpoint API Lengkap

Base URL: `/api/v1` (kecuali `/svc/*`). Endpoint bertanda ✔ butuh JWT
(`Authorization: Bearer <token>`).

## Auth
| Method | Path | Auth | Deskripsi |
|--------|------|:----:|-----------|
| POST | `/auth/register` | – | Registrasi user (201) |
| POST | `/auth/login` | – | Login → JWT |
| GET | `/auth/me` | ✔ | Info user saat ini |

## Dashboard & Fleet
| Method | Path | Auth | Deskripsi |
|--------|------|:----:|-----------|
| GET | `/dashboard` | ✔ | Statistik dashboard (mode-aware) |
| GET | `/fleet-summary` | – | Ringkasan armada (internal) |
| GET | `/health` | – | Health check service |

## Master Data
| Method | Path | Auth | Deskripsi |
|--------|------|:----:|-----------|
| GET/POST | `/jenis-alat-berat` | ✔ | List / create |
| GET/PUT/DELETE | `/jenis-alat-berat/{id}` | ✔ | Detail / update / delete |
| GET/POST | `/unit-tambang` | ✔ | List / create |
| GET/PUT/DELETE | `/unit-tambang/{id}` | ✔ | Detail / update / delete |

## Telemetry & Work Order
| Method | Path | Auth | Deskripsi |
|--------|------|:----:|-----------|
| POST | `/telemetry` | ✔ | Ingestion telemetri (33 kolom) |
| GET | `/telemetry/unit/{id}` | ✔ | Riwayat telemetri |
| GET/POST | `/work-orders` | ✔ | List / create WO |
| GET/PUT | `/work-orders/{id}` | ✔ | Detail / update WO |

## Analisa (MongoDB) & Health Analytics
| Method | Path | Auth | Deskripsi |
|--------|------|:----:|-----------|
| GET/POST | `/analisa` | ✔ | List / create laporan analisa |
| GET/PUT/DELETE | `/analisa/{id}` | ✔ | Detail / update / delete |
| GET | `/analisa/overview` | ✔ | Overview kesehatan armada |
| GET | `/analisa/unit/{id}` | ✔ | Analitik detail satu unit |

## PRATYAKSA ML API
| Method | Path | Auth | Deskripsi |
|--------|------|:----:|-----------|
| GET | `/pratyaksa/status` | – | Mode & reachability |
| GET | `/pratyaksa/fleet` | – | Data fleet |
| GET | `/pratyaksa/fleet/health` | – | Ringkasan health fleet |
| GET | `/pratyaksa/result/{asset_id}` | – | Hasil prediksi per asset |
| POST | `/pratyaksa/predict` | – | Prediksi (wajib 37 fitur) |
| POST | `/pratyaksa/workorder` | – | Generate WO dari ML |
| GET | `/pratyaksa/features` | – | 37 nama fitur sensor |
| GET | `/pratyaksa/explain/{id}` | – | SHAP explanation |
| POST | `/pratyaksa/reload-models` | – | Reload model |
| POST | `/pratyaksa/mode` | – | Ganti mode (live/simulasi/auto) |

## Live (MongoDB)
| Method | Path | Auth | Deskripsi |
|--------|------|:----:|-----------|
| GET | `/live/predictions` | – | Prediksi tersimpan |
| GET | `/live/predictions/{asset}/latest` | – | Prediksi terbaru |
| GET | `/live/fleet` | – | Fleet snapshot |
| GET | `/live/work-orders` | – | Work order live |
| GET | `/live/stats` | – | Statistik data live |

## Service (upload & alert)
| Method | Path | Auth | Deskripsi |
|--------|------|:----:|-----------|
| POST | `/svc/upload-model` | – | Upload model 3D (.glb/.gltf) |
| POST | `/svc/send-alert` | – | Kirim alert ke bot Telegram (gRPC) |

Swagger UI: `http://localhost:8080/docs`.

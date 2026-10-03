# ============================================================================
#  PRATYAKSA — Makefile
#  Predictive Analytics & Traceability for Heavy Asset Condition Surveillance
#  and Actualization.
#
#  Stack: FastAPI (Python) + SvelteKit (Svelte) + Telegram Bot (gRPC) + Nginx
#
#  Jalankan `make help` untuk melihat semua perintah yang tersedia.
# ============================================================================

# --- Shell & flags ----------------------------------------------------------
# Fail fast: any failing command (incl. in a pipeline) aborts the recipe.
SHELL := /bin/bash -eu -o pipefail
.DEFAULT_GOAL := help
.ONESHELL:

# --- Project metadata -------------------------------------------------------
PROJECT      := py-pratyaksa
COMPOSE      := docker compose
COMPOSE_FILE := docker-compose.yml
ENV_FILE     := .env
ENV_EXAMPLE  := .env.example

# --- Ports (override via env: `make up APP_PORT=8080`) ----------------------
APP_PORT            ?= 80
BACKEND_PORT        ?= 8080
FRONTEND_PORT       ?= 3000
POSTGRES_PORT       ?= 5432
MONGO_PORT          ?= 27017
MONGO_EXPRESS_PORT  ?= 8081
PGADMIN_PORT        ?= 5050
GRPC_PORT           ?= 50051

# --- Service / container names ---------------------------------------------
BACKEND_SVC    := backend
FRONTEND_SVC   := frontend
BOT_SVC        := telegram-bot
NGINX_SVC      := nginx
POSTGRES_SVC   := postgres
MONGO_SVC      := mongodb
MONGOEX_SVC    := mongo-express
PGADMIN_SVC    := pgadmin

# --- Local toolchain paths (manual / non-docker workflow) -------------------
# Absolute paths so they stay valid after `cd` inside recipes (incl. .ONESHELL).
ROOT           := $(CURDIR)
BACKEND_VENV   := $(ROOT)/backend/.venv/bin
BOT_VENV       := $(ROOT)/telegram_bot_grpc/.venv/bin
PY             := python3

# Resolve python/uvicorn executables (venv if present, else system).
BACKEND_PY     := $(if $(wildcard $(BACKEND_VENV)/python),$(BACKEND_VENV)/python,python3)
BACKEND_UV     := $(if $(wildcard $(BACKEND_VENV)/uvicorn),$(BACKEND_VENV)/uvicorn,uvicorn)
BOT_PY         := $(if $(wildcard $(BOT_VENV)/python),$(BOT_VENV)/python,python3)

# --- Local dev connection strings -------------------------------------------
DEV_DATABASE_URL ?= postgresql://pratyaksa:pratyaksa_secret@localhost:$(POSTGRES_PORT)/pratyaksa_db
DEV_MONGODB_URL  ?= mongodb://pratyaksa:pratyaksa_secret@localhost:$(MONGO_PORT)

# Colors
C_RESET := \033[0m
C_BOLD  := \033[1m
C_DIM   := \033[2m
C_AMB   := \033[33m
C_GRN   := \033[32m

# ============================================================================
#  HELP
# ============================================================================
.PHONY: help
help: ## Tampilkan daftar perintah yang tersedia
	@printf "$(C_BOLD)PRATYAKSA — Make targets$(C_RESET)\n\n"
	@printf "$(C_AMB)Pemakaian:$(C_RESET) make <target> [VAR=value]\n\n"
	@grep -hE '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(C_GRN)%-22s$(C_RESET) %s\n", $$1, $$2}'
	@printf "\n$(C_DIM)Docs: README.md · API_TESTING.md · catatan/$(C_RESET)\n"

# ============================================================================
#  DOCKER — LIFECYCLE
# ============================================================================
.PHONY: up
up: env ## Nyalakan seluruh stack (profil full) secara background
	$(COMPOSE) --profile full up -d --build
	@printf "$(C_GRN)✓$(C_RESET) Stack berjalan di http://localhost:$(APP_PORT) (login: admin@pratyaksa.id / admin123)\n"

.PHONY: up-db
up-db: env ## Nyalakan hanya database (PostgreSQL + MongoDB)
	$(COMPOSE) --profile db up -d
	@printf "$(C_GRN)✓$(C_RESET) Database Postgres:$(POSTGRES_PORT) Mongo:$(MONGO_PORT)\n"

.PHONY: up-backend
up-backend: env ## Nyalakan database + backend FastAPI (tanpa frontend)
	$(COMPOSE) --profile backend up -d --build
	@printf "$(C_GRN)✓$(C_RESET) Backend di http://localhost:$(BACKEND_PORT)\n"

.PHONY: up-bot
up-bot: env ## Nyalakan database + backend + Telegram bot
	$(COMPOSE) --profile full up -d --build $(BACKEND_SVC) $(BOT_SVC) $(POSTGRES_SVC) $(MONGO_SVC)
	@printf "$(C_GRN)✓$(C_RESET) Telegram bot (gRPC :$(GRPC_PORT)) berjalan\n"

.PHONY: up-tools
up-tools: env ## Nyalakan UI tools (Mongo Express + pgAdmin) — butuh stack utama jalan
	$(COMPOSE) --profile tools up -d
	@printf "$(C_GRN)✓$(C_RESET) mongo-express :$(MONGO_EXPRESS_PORT) · pgAdmin :$(PGADMIN_PORT)\n"

.PHONY: down
down: ## Hentikan & hapus seluruh container (data volume tetap aman)
	$(COMPOSE) --profile full --profile tools down
	@printf "$(C_GRN)✓$(C_RESET) Semua service dihentikan\n"

.PHONY: stop
stop: ## Hentikan container tanpa menghapusnya
	$(COMPOSE) --profile full stop

.PHONY: start
start: ## Jalankan kembali container yang sudah ada
	$(COMPOSE) --profile full start

.PHONY: restart
restart: ## Restart seluruh service
	$(COMPOSE) --profile full restart
	@printf "$(C_GRN)✓$(C_RESET) Semua service di-restart\n"

.PHONY: restart-backend
restart-backend: ## Restart backend saja
	$(COMPOSE) restart $(BACKEND_SVC)

.PHONY: restart-frontend
restart-frontend: ## Restart frontend saja
	$(COMPOSE) restart $(FRONTEND_SVC)

.PHONY: restart-bot
restart-bot: ## Restart Telegram bot saja
	$(COMPOSE) restart $(BOT_SVC)

.PHONY: build
build: env ## Build seluruh image Docker
	$(COMPOSE) --profile full build

.PHONY: build-backend
build-backend: ## Build image backend
	$(COMPOSE) build $(BACKEND_SVC)

.PHONY: build-frontend
build-frontend: ## Build image frontend
	$(COMPOSE) build $(FRONTEND_SVC)

.PHONY: build-bot
build-bot: ## Build image Telegram bot
	$(COMPOSE) build $(BOT_SVC)

.PHONY: rebuild
rebuild: ## Rebuild (tanpa cache) lalu nyalakan ulang seluruh stack
	$(COMPOSE) --profile full build --no-cache
	$(COMPOSE) --profile full up -d
	@printf "$(C_GRN)✓$(C_RESET) Stack di-rebuild dari nol\n"

.PHONY: pull
pull: ## Tarik image terbaru untuk base service (postgres/mongo/nginx)
	$(COMPOSE) pull --ignore-pull-failures || true

.PHONY: ps
ps: ## Lihat status container
	$(COMPOSE) --profile full --profile tools ps

.PHONY: ps-all
ps-all: ## Alias status semua container (termasuk berhenti)
	docker ps -a --filter "name=py-pratyaksa"

.PHONY: stats
stats: ## Lihat penggunaan resource container (CPU/RAM/Net)
	docker stats --no-stream $$(docker ps --filter "name=py-pratyaksa" --format '{{.Names}}')

# ============================================================================
#  DOCKER — LOGS & SHELL
# ============================================================================
.PHONY: logs
logs: ## Ikuti log semua service (Ctrl-C untuk keluar)
	$(COMPOSE) --profile full logs -f --tail=100

.PHONY: logs-backend
logs-backend: ## Ikuti log backend
	$(COMPOSE) logs -f --tail=100 $(BACKEND_SVC)

.PHONY: logs-frontend
logs-frontend: ## Ikuti log frontend
	$(COMPOSE) logs -f --tail=100 $(FRONTEND_SVC)

.PHONY: logs-bot
logs-bot: ## Ikuti log Telegram bot
	$(COMPOSE) logs -f --tail=100 $(BOT_SVC)

.PHONY: logs-nginx
logs-nginx: ## Ikuti log nginx
	$(COMPOSE) logs -f --tail=100 $(NGINX_SVC)

.PHONY: logs-db
logs-db: ## Ikuti log database (postgres + mongo)
	$(COMPOSE) logs -f --tail=100 $(POSTGRES_SVC) $(MONGO_SVC)

.PHONY: sh-backend
sh-backend: ## Masuk ke shell container backend
	$(COMPOSE) exec $(BACKEND_SVC) bash || $(COMPOSE) exec $(BACKEND_SVC) sh

.PHONY: sh-frontend
sh-frontend: ## Masuk ke shell container frontend
	$(COMPOSE) exec $(FRONTEND_SVC) sh

.PHONY: sh-bot
sh-bot: ## Masuk ke shell container Telegram bot
	$(COMPOSE) exec $(BOT_SVC) bash || $(COMPOSE) exec $(BOT_SVC) sh

.PHONY: sh-nginx
sh-nginx: ## Masuk ke shell container nginx
	$(COMPOSE) exec $(NGINX_SVC) sh

.PHONY: sh-postgres
sh-postgres: ## Masuk ke psql (PostgreSQL)
	$(COMPOSE) exec $(POSTGRES_SVC) psql -U pratyaksa -d pratyaksa_db

.PHONY: sh-mongo
sh-mongo: ## Masuk ke mongosh (MongoDB)
	$(COMPOSE) exec $(MONGO_SVC) mongosh -u pratyaksa -p pratyaksa_secret --authenticationDatabase admin

.PHONY: inspect
inspect: ## Tampilkan konfigurasi compose yang sudah di-resolve
	$(COMPOSE) --profile full config

# ============================================================================
#  ENV / CONFIG
# ============================================================================
.PHONY: env
env: ## Buat .env dari .env.example jika belum ada
	@if [ ! -f $(ENV_FILE) ]; then \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		printf "$(C_AMB)⚠$(C_RESET)  .env dibuat dari $(ENV_EXAMPLE) — sesuaikan bila perlu\n"; \
	fi

.PHONY: env-force
env-force: ## Timpa .env dari contoh (PERINGATAN: menimpa konfigurasi)
	cp $(ENV_EXAMPLE) $(ENV_FILE)
	@printf "$(C_GRN)✓$(C_RESET) .env ditimpa dari $(ENV_EXAMPLE)\n"

.PHONY: env-check
env-check: ## Validasi docker-compose (config) tanpa menjalankan
	$(COMPOSE) -f $(COMPOSE_FILE) config -q && printf "$(C_GRN)✓$(C_RESET) docker-compose valid\n"

.PHONY: compose-version
compose-version: ## Tampilkan versi Docker & Compose
	@docker --version
	@$(COMPOSE) version

# ============================================================================
#  LOCAL DEV (non-docker)
# ============================================================================
.PHONY: dev-backend
dev-backend: ## Jalankan backend lokal (uvicorn --reload)
	cd backend && DATABASE_URL="$(DEV_DATABASE_URL)" MONGODB_URL="$(DEV_MONGODB_URL)" \
		$(BACKEND_UV) app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

.PHONY: dev-frontend
dev-frontend: ## Jalankan frontend lokal (vite dev)
	cd frontend && pnpm dev

.PHONY: dev-bot
dev-bot: ## Jalankan Telegram bot lokal
	cd telegram_bot_grpc && BACKEND_URL="http://localhost:$(BACKEND_PORT)" $(BOT_PY) main.py

.PHONY: dev
dev: ## Info: jalankan backend + frontend di dua terminal terpisah
	@printf "$(C_AMB)Jalankan di terminal terpisah:$(C_RESET)\n"
	@printf "  1) $(C_GRN)make dev-backend$(C_RESET)\n"
	@printf "  2) $(C_GRN)make dev-frontend$(C_RESET)\n"

.PHONY: install-backend
install-backend: ## Buat venv backend + install dependency dev
	cd backend && $(PY) -m venv .venv && .venv/bin/pip install --upgrade pip \
		&& .venv/bin/pip install -r requirements-dev.txt
	@printf "$(C_GRN)✓$(C_RESET) Backend venv siap\n"

.PHONY: install-bot
install-bot: ## Buat venv bot + install dependency dev
	cd telegram_bot_grpc && $(PY) -m venv .venv && .venv/bin/pip install --upgrade pip \
		&& .venv/bin/pip install -r requirements-dev.txt
	@printf "$(C_GRN)✓$(C_RESET) Bot venv siap\n"

.PHONY: install-frontend
install-frontend: ## Install dependency frontend (pnpm)
	cd frontend && corepack enable && pnpm install
	@printf "$(C_GRN)✓$(C_RESET) Frontend deps siap\n"

.PHONY: install
install: install-backend install-bot install-frontend ## Install semua dependency (backend, bot, frontend)
	@printf "$(C_GRN)✓$(C_RESET) Semua dependency terpasang\n"

# ============================================================================
#  BUILD / CHECK (frontend)
# ============================================================================
.PHONY: check
check: ## Type-check frontend (svelte-check)
	cd frontend && pnpm check

.PHONY: frontend-build
frontend-build: ## Build frontend produksi (adapter-node)
	cd frontend && pnpm build
	@printf "$(C_GRN)✓$(C_RESET) Frontend ter-build ke frontend/build\n"

.PHONY: frontend-preview
frontend-preview: ## Preview hasil build frontend
	cd frontend && pnpm preview

# ============================================================================
#  TESTING
# ============================================================================
.PHONY: test
test: test-backend test-bot test-frontend ## Jalankan semua test (backend + bot + frontend check)
	@printf "\n$(C_GRN)✓$(C_RESET) $(C_BOLD)Semua test selesai$(C_RESET)\n"

.PHONY: test-backend
test-backend: ## Test backend (pytest)
	@printf "$(C_BOLD)== Backend tests ==$(C_RESET)\n"
	cd backend && $(BACKEND_PY) -m pytest -q

.PHONY: test-bot
test-bot: ## Test Telegram bot (pytest)
	@printf "$(C_BOLD)== Bot tests ==$(C_RESET)\n"
	cd telegram_bot_grpc && $(BOT_PY) -m pytest -q

.PHONY: test-frontend
test-frontend: ## Test/type-check frontend
	@printf "$(C_BOLD)== Frontend check ==$(C_RESET)\n"
	cd frontend && pnpm check

.PHONY: test-live
test-live: ## Uji integrasi Live API (butuh backend berjalan)
	BACKEND_URL="http://localhost:$(BACKEND_PORT)" bash test/test_live_api.sh

.PHONY: test-api
test-api: ## Smoke-test endpoint utama (butuh backend berjalan di :$(BACKEND_PORT))
	@printf "$(C_BOLD)== API smoke test ==$(C_RESET)\n"
	@for ep in /api/v1/health /api/v1/fleet-summary /api/v1/pratyaksa/status \
		/api/v1/pratyaksa/fleet /api/v1/pratyaksa/fleet/health /api/v1/pratyaksa/features; do \
		code=$$(curl -s -m 5 -o /dev/null -w "%{http_code}" "http://localhost:$(BACKEND_PORT)$$ep"); \
		printf "  %s  %s\n" "$$code" "$$ep"; \
	done

.PHONY: test-all
test-all: test test-live ## Semua test (unit + integrasi live)

# ============================================================================
#  DATABASE — MIGRATIONS & DUMP
# ============================================================================
.PHONY: migrate
migrate: ## Jalankan migrasi SQL backend (via container backend)
	@printf "$(C_GRN)…$(C_RESET) Migrasi dijalankan otomatis saat backend start\n"
	$(COMPOSE) exec $(BACKEND_SVC) sh -lc 'echo "schema_migrations:"; ' || true

.PHONY: db-reset
db-reset: ## HAPUS volume DB lalu nyalakan ulang database (DESTRUKTIF!)
	@printf "$(C_AMB)⚠$(C_RESET)  Menghapus volume PostgreSQL & MongoDB...\n"
	$(COMPOSE) --profile full rm -sf $(POSTGRES_SVC) $(MONGO_SVC) 2>/dev/null || true
	docker volume rm py_pratyaksa_postgres_data py_pratyaksa_mongo_data 2>/dev/null || true
	$(COMPOSE) --profile db up -d
	@printf "$(C_GRN)✓$(C_RESET) Database di-reset (kosong)\n"

.PHONY: db-dump
db-dump: ## Backup PostgreSQL ke backups/pratyaksa-<timestamp>.sql
	@mkdir -p backups
	$(COMPOSE) exec -T $(POSTGRES_SVC) pg_dump -U pratyaksa pratyaksa_db \
		> backups/pratyaksa-$$(date +%Y%m%d-%H%M%S).sql
	@printf "$(C_GRN)✓$(C_RESET) Dump tersimpan di backups/\n"

.PHONY: db-restore
db-restore: ## Restore PostgreSQL dari FILE=backups/xx.sql
	@if [ -z "$(FILE)" ]; then printf "Gunakan: make db-restore FILE=backups/pratyaksa-XXXX.sql\n"; exit 1; fi
	$(COMPOSE) exec -T $(POSTGRES_SVC) psql -U pratyaksa -d pratyaksa_db < $(FILE)
	@printf "$(C_GRN)✓$(C_RESET) Restore selesai dari $(FILE)\n"

.PHONY: db-seed
db-seed: ## Cek jumlah baris tabel utama (verifikasi seed)
	$(COMPOSE) exec -T $(POSTGRES_SVC) psql -U pratyaksa -d pratyaksa_db \
		-c "SELECT 'users' t, count(*) FROM users UNION ALL SELECT 'jenis_alat_berat', count(*) FROM jenis_alat_berat UNION ALL SELECT 'unit_tambang', count(*) FROM unit_tambang UNION ALL SELECT 'work_orders', count(*) FROM work_orders;"

.PHONY: db-tables
db-tables: ## Tampilkan daftar tabel PostgreSQL
	$(COMPOSE) exec -T $(POSTGRES_SVC) psql -U pratyaksa -d pratyaksa_db -c "\dt"

# ============================================================================
#  MAINTENANCE / CLEAN
# ============================================================================
.PHONY: prune
prune: ## Bersihkan image/container/network Docker yang tak terpakai
	docker system prune -f
	@printf "$(C_GRN)✓$(C_RESET) Docker pruned\n"

.PHONY: clean
clean: ## Bersihkan artefak build & cache Python/Node (aman)
	rm -rf frontend/build frontend/.svelte-kit
	find backend telegram_bot_grpc -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
	find backend telegram_bot_grpc -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/media
	@printf "$(C_GRN)✓$(C_RESET) Artefak build & cache dibersihkan\n"

.PHONY: clean-all
clean-all: down clean ## Hentikan stack + bersihkan (volume DB tidak dihapus)
	@printf "$(C_GRN)✓$(C_RESET) Clean-all selesai\n"

.PHONY: reset
reset: down ## Reset penuh: down + hapus volume + clean (DESTRUKTIF!)
	@printf "$(C_AMB)⚠$(C_RESET)  Menghapus SEMUA volume (DB, media, bot)...\n"
	$(COMPOSE) --profile full down -v
	$(MAKE) clean
	@printf "$(C_GRN)✓$(C_RESET) Reset penuh selesai\n"

.PHONY: health
health: ## Cek kesehatan semua endpoint via Nginx/port aplikasi
	@printf "$(C_BOLD)== Health check ==$(C_RESET)\n"
	@for ep in /api/v1/health /api/v1/pratyaksa/status /api/v1/fleet-summary; do \
		code=$$(curl -s -m 5 -o /dev/null -w "%{http_code}" "http://localhost:$(APP_PORT)$$ep"); \
		printf "  %s  %s\n" "$$code" "$$ep"; \
	done

.PHONY: urls
urls: ## Tampilkan URL penting layanan
	@printf "$(C_BOLD)URL Layanan$(C_RESET)\n"
	@printf "  App / Nginx     : http://localhost:$(APP_PORT)\n"
	@printf "  Backend API     : http://localhost:$(BACKEND_PORT)/api/v1  (docs: /docs)\n"
	@printf "  Frontend        : http://localhost:$(FRONTEND_PORT)\n"
	@printf "  Swagger UI      : http://localhost:$(BACKEND_PORT)/docs\n"
	@printf "  mongo-express   : http://localhost:$(MONGO_EXPRESS_PORT)\n"
	@printf "  pgAdmin         : http://localhost:$(PGADMIN_PORT)\n"
	@printf "  ML API (ext)    : http://192.168.101.3:6000\n"

.PHONY: version
version: ## Tampilkan versi stack
	@printf "$(C_BOLD)$(PROJECT)$(C_RESET) — FastAPI + SvelteKit + Telegram Bot (gRPC)\n"
	@printf "  Backend  : v%s\n" "$$(sed -n 's/.*version=//p' backend/app/main.py | tr -d '\"' | head -1)"
	@printf "  Frontend : v%s\n" "$$(sed -n 's/.*\"version\": \"\([^\"]*\)\".*/\1/p' frontend/package.json | head -1)"
	@printf "  Compose  : $$(docker compose version --short 2>/dev/null || echo n/a)\n"

# ============================================================================
#  CI — rantai kualitas lengkap
# ============================================================================
.PHONY: ci
ci: env-check test ## Rantai CI: validasi config + semua test
	@printf "$(C_GRN)✓$(C_RESET) CI selesai\n"

.PHONY: ci-full
ci-full: env-check test frontend-build ## CI lengkap: config + test + build frontend
	@printf "$(C_GRN)✓$(C_RESET) CI-full selesai\n"

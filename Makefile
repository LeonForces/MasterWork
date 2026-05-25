SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE_DETECTED := $(shell if command -v docker-compose >/dev/null 2>&1; then echo docker-compose; else echo "docker compose"; fi)
COMPOSE ?= $(COMPOSE_DETECTED)
E2E_COMPOSE ?= $(COMPOSE) -f docker-compose.e2e.yml -p masterdegree_e2e
PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest
UI_NPM ?= npm --prefix services/ui
TAIL ?= 200
SERVICES ?=

API_TESTS := services/api/tests
ANALYTICS_TESTS := services/analytics-worker/tests
INTEGRATION_TESTS := services/integration-worker/tests

API_BASE ?= http://localhost:8000
E2E_API_BASE ?= http://localhost:18000
E2E_WEBHOOK_BASE ?= http://localhost:18090
SMOKE_USERNAME ?= admin
SMOKE_PASSWORD ?= admin12345
SMOKE_CAMERA_SOURCE ?= /app/videos/V_DRONE_009.mp4
ACCEPTANCE_RESULTS ?= docs/MasterWork/REPORT/LaTeX/acceptance_results_2026-05-13.json

REPORT_DIR ?= docs/MasterWork/REPORT/LaTeX
REPORT_MAIN ?= main
REPORT_TEX_IMAGE ?= texlive/texlive:latest
REPORT_WORKDIR ?= /work/$(REPORT_DIR)

.PHONY: help bootstrap verify env-init env-check compose-check build rebuild pull up up-d down down-v restart ps
.PHONY: logs logs-api logs-analytics logs-integration logs-ui logs-db
.PHONY: migrate-up migrate-down api-shell analytics-shell integration-shell db-shell rabbitmq-shell
.PHONY: api-test analytics-test integration-test ui-test test test-all
.PHONY: ui-install ui-build ui-dev smoke-e2e acceptance-e2e e2e-up-d e2e-down e2e-migrate-up e2e-smoke e2e-acceptance e2e-acceptance-artifact clean
.PHONY: report-pdf report-clean report-check

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make <target>\n\nTargets:\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: env-init compose-check ui-install ## Initialize local dev environment

verify: compose-check test ui-test ui-build ## Run core project checks

env-init: ## Create .env from .env.example if missing
	@if [ ! -f .env ]; then cp .env.example .env; echo ".env created from .env.example"; else echo ".env already exists"; fi

env-check: ## Ensure .env exists
	@test -f .env || (echo ".env not found. Run 'make env-init' first."; exit 1)

compose-check: env-init ## Validate docker-compose config
	$(COMPOSE) config -q

pull: ## Pull remote images
	$(COMPOSE) pull

build: env-init ## Build all images
	$(COMPOSE) build

rebuild: env-init ## Rebuild all images without cache
	$(COMPOSE) build --no-cache

up: env-init ## Start full stack in foreground
	$(COMPOSE) up --build

up-d: env-init ## Start full stack in background
	$(COMPOSE) up --build -d

down: ## Stop and remove stack
	$(COMPOSE) down

down-v: ## Stop stack and remove volumes
	$(COMPOSE) down -v --remove-orphans

restart: ## Restart stack in background
	$(MAKE) down
	$(MAKE) up-d

ps: ## Show services status
	$(COMPOSE) ps

logs: ## Tail logs for all or selected services (SERVICES="api ui")
	$(COMPOSE) logs -f --tail=$(TAIL) $(SERVICES)

logs-api: ## Tail API logs
	$(COMPOSE) logs -f --tail=$(TAIL) api

logs-analytics: ## Tail analytics-worker logs
	$(COMPOSE) logs -f --tail=$(TAIL) analytics-worker

logs-integration: ## Tail integration-worker logs
	$(COMPOSE) logs -f --tail=$(TAIL) integration-worker

logs-ui: ## Tail UI logs
	$(COMPOSE) logs -f --tail=$(TAIL) ui

logs-db: ## Tail postgres and rabbitmq logs
	$(COMPOSE) logs -f --tail=$(TAIL) postgres rabbitmq

migrate-up: env-init ## Apply Alembic migrations in API container
	$(COMPOSE) run --rm api alembic upgrade head

migrate-down: env-init ## Rollback one Alembic migration in API container
	$(COMPOSE) run --rm api alembic downgrade -1

api-shell: env-init ## Open shell in API container
	$(COMPOSE) run --rm api /bin/sh

analytics-shell: env-init ## Open shell in analytics-worker container
	$(COMPOSE) run --rm analytics-worker /bin/sh

integration-shell: env-init ## Open shell in integration-worker container
	$(COMPOSE) run --rm integration-worker /bin/sh

db-shell: env-init ## Open psql shell in postgres container
	$(COMPOSE) exec postgres sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

rabbitmq-shell: env-init ## Open shell in RabbitMQ container
	$(COMPOSE) exec rabbitmq /bin/bash

api-test: ## Run API tests
	$(PYTEST) -q $(API_TESTS)

analytics-test: ## Run analytics-worker tests
	$(PYTEST) -q $(ANALYTICS_TESTS)

integration-test: ## Run integration-worker tests
	$(PYTEST) -q $(INTEGRATION_TESTS)

ui-test: ui-install ## Run UI tests (Vitest)
	$(UI_NPM) run test -- --passWithNoTests

test: api-test analytics-test integration-test ## Run backend test suite

test-all: test ui-test ui-build ## Run backend tests + UI tests + UI build

ui-install: ## Install UI dependencies from lockfile
	$(UI_NPM) ci --no-fund --no-audit

ui-build: ui-install ## Build UI
	$(UI_NPM) run build

ui-dev: ui-install ## Run UI dev server
	$(UI_NPM) run dev

smoke-e2e: ## Run API smoke scenario (requires running stack)
	$(PYTHON) scripts/smoke_e2e.py \
		--api-base $(API_BASE) \
		--username $(SMOKE_USERNAME) \
		--password $(SMOKE_PASSWORD) \
		--camera-source $(SMOKE_CAMERA_SOURCE)

acceptance-e2e: ## Run full acceptance checks (functional + RBAC + RabbitMQ/webhook reliability)
	$(PYTHON) scripts/acceptance_e2e.py \
		--api-base $(API_BASE) \
		--webhook-base http://localhost:8090 \
		--username $(SMOKE_USERNAME) \
		--password $(SMOKE_PASSWORD) \
		--compose-bin "$(COMPOSE)"

e2e-up-d: env-init ## Start isolated E2E stack on shifted host ports
	$(E2E_COMPOSE) up --build -d postgres rabbitmq webhook-mock api integration-worker ui

e2e-down: ## Stop isolated E2E stack
	$(E2E_COMPOSE) down --remove-orphans

e2e-migrate-up: env-init ## Apply migrations in isolated E2E stack
	$(E2E_COMPOSE) run --rm api alembic upgrade head

e2e-smoke: ## Run smoke flow against isolated E2E API
	$(PYTHON) scripts/smoke_e2e.py \
		--api-base $(E2E_API_BASE) \
		--username $(SMOKE_USERNAME) \
		--password $(SMOKE_PASSWORD) \
		--camera-source $(SMOKE_CAMERA_SOURCE)

e2e-acceptance: ## Run acceptance checks against isolated E2E stack
	$(PYTHON) scripts/acceptance_e2e.py \
		--api-base $(E2E_API_BASE) \
		--webhook-base $(E2E_WEBHOOK_BASE) \
		--username $(SMOKE_USERNAME) \
		--password $(SMOKE_PASSWORD) \
		--compose-bin "$(E2E_COMPOSE)"

e2e-acceptance-artifact: ## Save isolated E2E acceptance JSON to the report directory
	@$(PYTHON) scripts/acceptance_e2e.py \
		--api-base $(E2E_API_BASE) \
		--webhook-base $(E2E_WEBHOOK_BASE) \
		--username $(SMOKE_USERNAME) \
		--password $(SMOKE_PASSWORD) \
		--compose-bin "$(E2E_COMPOSE)" > $(ACCEPTANCE_RESULTS)
	@$(PYTHON) -m json.tool $(ACCEPTANCE_RESULTS) >/dev/null
	@echo "Saved acceptance artifact to $(ACCEPTANCE_RESULTS)"

report-pdf: ## Build master's thesis PDF via dockerized TeX Live (xelatex+biber)
	docker run --rm \
		-v "$(PWD):/work" \
		-w "$(REPORT_WORKDIR)" \
		$(REPORT_TEX_IMAGE) /bin/sh -lc "\
			xelatex -interaction=nonstopmode -halt-on-error $(REPORT_MAIN).tex && \
			biber $(REPORT_MAIN) && \
			xelatex -interaction=nonstopmode -halt-on-error $(REPORT_MAIN).tex && \
			xelatex -interaction=nonstopmode -halt-on-error $(REPORT_MAIN).tex"

report-clean: ## Remove LaTeX auxiliary files for thesis report
	find $(REPORT_DIR) -maxdepth 1 -type f \( \
		-name "$(REPORT_MAIN).aux" -o \
		-name "$(REPORT_MAIN).bbl" -o \
		-name "$(REPORT_MAIN).bcf" -o \
		-name "$(REPORT_MAIN).blg" -o \
		-name "$(REPORT_MAIN).log" -o \
		-name "$(REPORT_MAIN).out" -o \
		-name "$(REPORT_MAIN).run.xml" -o \
		-name "$(REPORT_MAIN).toc" -o \
		-name "$(REPORT_MAIN).lof" -o \
		-name "$(REPORT_MAIN).lot" -o \
		-name "$(REPORT_MAIN).xdv" \) -delete

report-check: report-pdf ## Check report build for undefined refs/citations and unresolved markers
	@LOG_FILE="$(REPORT_DIR)/$(REPORT_MAIN).log"; \
	if rg -n "Citation.*undefined|Reference.*undefined|There were undefined references|undefined citations|Rerun to get cross-references right" "$$LOG_FILE"; then \
		echo "Report check failed: unresolved citations/references found in $$LOG_FILE"; \
		exit 1; \
	fi
	@for f in "$(REPORT_DIR)/$(REPORT_MAIN).toc" "$(REPORT_DIR)/$(REPORT_MAIN).lof" "$(REPORT_DIR)/$(REPORT_MAIN).lot"; do \
		if [ -f "$$f" ] && rg -n "\\?\\?" "$$f"; then \
			echo "Report check failed: unresolved markers found in $$f"; \
			exit 1; \
		fi; \
	done
	@echo "Report check passed: no unresolved refs/citations found."

clean: ## Remove local temporary artifacts
	rm -f test_api.db
	rm -rf .pytest_cache
	rm -rf services/ui/dist

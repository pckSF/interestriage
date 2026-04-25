UV := $(HOME)/.local/bin/uv
DOCKER_COMPOSE_DEV := docker compose -f infra/dev/docker-compose.yml
IMAGE_TAG ?= dev
DOCKER ?= docker
PIP_AUDIT_IMAGE ?= interestriage/pip-audit:local
PIP_AUDIT_ARGS ?= . --ignore-vuln CVE-2026-3219

.PHONY: dev test test-ssrf test-audio build down pip-audit-container-build pip-audit-container

dev:
	@npm ci
	@$(UV) sync --extra dev
	@npm run build -w shared
	@npm run build -w web
	@$(DOCKER_COMPOSE_DEV) up -d --build

test:
	@npm ci
	@$(UV) sync --extra dev
	@npm run lint
	@npm run typecheck
	@$(UV) run pytest -q

test-ssrf:
	@$(DOCKER_COMPOSE_DEV) --profile security-tests up -d --build evil-server backend parser-sandbox
	@$(UV) run pytest -q tests/integration/test_ssrf_scaffold.py
	@$(DOCKER_COMPOSE_DEV) --profile security-tests down --remove-orphans

test-audio:
	@$(UV) sync --extra dev
	@$(UV) run pytest -q -m audio_real

build:
	@npm ci
	@npm run build -w shared
	@npm run build -w web
	@npm run build -w extension
	@mkdir -p dist
	@rm -rf dist/dashboard
	@cp -R web/dist dist/dashboard
	@cp extension/dist/extension.zip dist/extension.zip
	@docker build -f infra/Dockerfile.backend -t interestriage/backend:$(IMAGE_TAG) .
	@docker build -f infra/Dockerfile.dashboard -t interestriage/dashboard:$(IMAGE_TAG) .

down:
	@$(DOCKER_COMPOSE_DEV) down --remove-orphans

pip-audit-container-build:
	@command -v $(DOCKER) >/dev/null 2>&1 || (echo "docker CLI is required for pip-audit-container" && exit 1)
	@$(DOCKER) build -f infra/Dockerfile.pip-audit -t $(PIP_AUDIT_IMAGE) .

pip-audit-container: pip-audit-container-build
	@$(DOCKER) run --rm \
		-v "$(PWD):/workspace:ro" \
		-w /workspace \
		$(PIP_AUDIT_IMAGE) $(PIP_AUDIT_ARGS)

.PHONY: services up down logs-migrate migrate up-core up-app deploy routes

services:
	docker compose config --services

up:
	docker compose up -d

down:
	docker compose down

logs-migrate:
	docker compose logs migrate --tail=200

migrate:
	docker compose run --rm migrate

up-core:
	docker compose up -d db redis

up-app:
	docker compose up -d api worker frontend

deploy: up-core migrate up-app

routes:
	docker compose exec api python - <<'PY'
from app.api.main import app
for route in app.routes:
    print(getattr(route, "path", None))
PY

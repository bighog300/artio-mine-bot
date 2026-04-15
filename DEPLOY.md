# Deployment (Docker Compose)

This repository is deployed with Docker Compose using these service names:

- `db`
- `redis`
- `migrate`
- `api`
- `worker`
- `frontend`

> Use `api`, **not** `app`.

## Why migrations must run in Docker

Do **not** run `alembic upgrade head` on the host for Docker deployments.

In this repo, migration/runtime dependencies are installed in the container image, and the compose flow is designed to run migrations via compose services.

## Safe deploy flow

```bash
docker compose up -d db redis
docker compose run --rm migrate
docker compose up -d api worker frontend
```

Equivalent shortcut:

```bash
make deploy
```

## Troubleshooting

If startup fails because migrations failed, inspect migration logs:

```bash
docker compose logs migrate --tail=200
```

To inspect available service names:

```bash
docker compose config --services
```

## Compose dependency behavior

`api` and `worker` are configured to wait until `migrate` completes successfully before starting.

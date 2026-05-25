# Real-Time Video Analytics Platform (E2E MVP)

Monorepo with isolated services:

- `services/api` - FastAPI control plane (`JWT + RBAC`, config CRUD, events, health/metrics)
- `services/analytics-worker` - capture/inference/tracking/rule engine + `events/event_outbox`
- `services/integration-worker` - outbox publisher to RabbitMQ + webhook delivery with retry/DLQ
- `services/ui` - React SPA (`login`, `dashboard`, `cameras`, `zones`, `rules`, `events`, `status`)
- `services/webhook-mock` - test consumer for delivery validation
- `infra/prometheus`, `infra/grafana` - observability stack
- `contracts` - shared schemas/contracts

## Quick Start

1. Initialize env and dependencies:

```bash
make bootstrap
```

If you already had an older `.env`, ensure `JWT_SECRET_KEY` is at least 32 chars.

2. Start stack:

```bash
make up-d
```

3. Open:

- API docs: `http://localhost:8000/docs`
- UI: `http://localhost:4173`
- RabbitMQ Management: `http://localhost:15672`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Webhook mock: `http://localhost:8090`

## Drone Detection Demo

The stack is configured to use the trained drone detector and the uploaded demo video:

- model: `runs/detect/runs/train/small_detection/weights/best.pt`
- video: `videos/V_DRONE_009.mp4`
- analytics container paths: `/app/models/best.pt` and `/app/videos/V_DRONE_009.mp4`

After `make up-d`, open the UI and go to `Drone demo`. The API seeds an active demo camera automatically when `DEMO_DRONE_ENABLED=true`, and the analytics worker writes current drone tracks to `/api/v1/tracks` plus demo rule events to `/api/v1/events`. With `DEMO_DRONE_EXCLUSIVE=true`, old non-demo cameras are marked inactive so the worker focuses on the uploaded video.

## Default Credentials

- Admin username: `admin`
- Admin password: `admin12345`

Configured in `.env` (`DEFAULT_ADMIN_USERNAME`, `DEFAULT_ADMIN_PASSWORD`).

## Notes

- Baseline is CPU-first; hardware acceleration is a future optimization path and is not part of the current accepted result.
- Event contract baseline is in `contracts/event.schema.v1.json`.

## Validation Commands

```bash
make verify
```

API smoke flow (after stack is up):

```bash
make smoke-e2e
```

Full acceptance flow (functional + security + reliability):

```bash
make acceptance-e2e
```

Isolated acceptance flow when default host ports are occupied:

```bash
make e2e-up-d
make e2e-migrate-up
make e2e-smoke
make e2e-acceptance-artifact
```

The isolated profile exposes the API at `http://localhost:18000` and the UI at `http://localhost:14173`.

Sample acceptance run artifact:

- `docs/MasterWork/REPORT/LaTeX/acceptance_results_2026-05-13.json`

Useful operations:

```bash
make ps
make logs SERVICES="api integration-worker"
make migrate-up
make down
```

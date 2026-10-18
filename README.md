# bakery-ops

Recipe costing, inventory and production tracking for bakeries and small food producers.
Working repo name; the product name is not decided yet (see `docs/decision-log.md`, D46).

**Status:** foundation only. Product discovery (baker interviews) is running in parallel;
features beyond the costing core wait for what interviews show.

## Docs
- [`CLAUDE.md`](CLAUDE.md) — rules for every coding session
- [`docs/product-plan.md`](docs/product-plan.md) — goals, process, feature specs, open questions
- [`docs/technical-design.md`](docs/technical-design.md) — architecture, data model, business rules
- [`docs/decision-log.md`](docs/decision-log.md) — every decision and the alternatives rejected

## Stack
Django + Django REST Framework + PostgreSQL · React + TypeScript + Vite · GitHub Actions CI

## Local setup
Requirements: Docker, [uv](https://docs.astral.sh/uv/), Node 22.

```bash
cp .env.example .env            # then edit values
docker compose up -d db         # Postgres 16 on localhost:5432

cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver    # http://localhost:8000/api/health/

cd ../web
npm install
npm run dev                          # http://localhost:5173 (proxies /api to Django)
```

## Checks (same as CI)
```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest
cd web && npm run lint && npm run build
```

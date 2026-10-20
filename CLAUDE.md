# CLAUDE.md — Baking App

Read this at the start of every session. Full context lives in:
- `docs/product-plan.md` — goals, PM process, feature specs, open questions
- `docs/technical-design.md` — stack, data model, business rules, infrastructure
- `docs/decision-log.md` — every decision, why, and rejected alternatives

Last updated: 2026-10-19. Status: foundation in progress — repo + CI done; tenancy (custom user, Organization, Membership, org-scoped API base) done; first org-owned model `Ingredient`. Next: unit/density conversion (TDD). Repo: `bakery-ops`.

## What this is
A multi-tenant web app for bakeries and small food producers: recipes with version history, ingredient costing, purchase log, inventory ledger, batch logging, finished-goods tracking, production planning, pricing/margins, and AI recipe parsing.

Built by T (Tanner). **Primary goal: product management experience.** Secondary: AI engineering skill (differentiator). Tertiary: readiness for a possible food business.
**Tie-breaker: if a feature isn't backed by user research, it doesn't get built.** Curiosity work goes on a separate branch.

## Stack
- **Backend:** Python, Django, Django REST Framework, PostgreSQL
- **Frontend:** TypeScript, React, Vite, React Router (library mode), TanStack Query, React Hook Form + Zod, shadcn/ui + Tailwind, Recharts
- **API types:** drf-spectacular → openapi-typescript. Never hand-write API types.
- **AI:** Anthropic SDK (Python), Pydantic validation, provider behind a thin internal interface. No LangChain.
- **Files:** Cloudflare R2 via django-storages (S3 API), private bucket, signed URLs
- **Hosting:** Render. One web service: Django serves the API and the built SPA (WhiteNoise) on one origin. Managed Postgres.
- **Auth:** Django session auth + CSRF (same origin). No JWT.
- **Monitoring:** Sentry (Django + React), PostHog (product analytics), uptime monitor
- **CI:** GitHub Actions on every push: pytest, mypy, ruff, tsc, ESLint. Deploy on green `main`.
- **Local dev:** Docker Compose for Postgres; uv for Python deps; Vite proxies `/api` to Django. Secrets in `.env` (never committed).

## Non-negotiable data rules
1. `DECIMAL` for all money and quantities. Never float.
2. Every tenant-owned model inherits `organizations.models.OrgOwnedModel`; app code reads via `Model.objects.for_org(org)`. Every API view over bakery data subclasses `organizations.api.OrgScopedViewSet` (filters to the active bakery, saves new rows to it, ignores any `organization` in the request body). Other bakeries' rows return **404**, never 403. Active bakery: the user's only membership, else the `X-Organization` header (must be a membership; missing → 400). `tests/test_architecture.py` enforces all of this — never weaken it.
3. Append-only tables: ledger entries, purchases, recipe versions, product versions, batches. Never UPDATE or DELETE them. Fix mistakes with **reversal entries** linked to the original.
4. Store metric only (g, ml, each). Convert for display per org setting.
5. Volume→weight requires ingredient `density_g_per_ml`; "each"→weight requires `grams_per_each`. If missing, **raise and ask the user** — never guess.
6. Count-based products: stock as **integer base units** (smallest portion). Weight-based products: `DECIMAL` grams.
7. Live recipe costing uses the **latest purchase price**. Batch cost snapshots use **FIFO lot cost**; any shortfall beyond available stock is costed at latest price and the batch is flagged `cost_is_estimated`.
8. Negative stock is allowed, with a warning. Never block a batch log.
9. Sub-recipes always use the **latest version**. Cost rolls up recursively. Cycles are rejected on save. Logging a parent batch auto-creates `consumed` entries for sub-recipe products.
10. Recipe versions are created only by explicit "save as new version" with a **required change note**. Edits in between live in an autosaved draft.
11. Changing a product's portion definition creates a **new product version**.

## Testing rules
- **Calculation core — strict TDD (tests first):** unit conversion, density conversion, scaling, step-time scaling, cost rollups incl. sub-recipes, cycle detection, margins, ledger sums, FIFO consumption, negative-stock costing, sell-unit conversion, production-plan math, org isolation.
- **API/DB:** pytest + Django test client against real Postgres (not SQLite).
- **UI:** a few Playwright tests on critical flows only (create recipe → scale → see cost; log batch; log sale).
- **AI:** eval set of 30–50 real messy recipes with expected output; score on every prompt/model change. CI uses recorded fixtures; live evals run on demand.

## Naming
- Repo is `bakery-ops`; brand name is undecided. **Never put a brand name in code identifiers.**
- Django project `config/`; apps by domain: `accounts` (custom User), `organizations`, `recipes`, `inventory`, `production`, `parsing`. Frontend package: `web`.
- All user-facing brand strings read from the single `APP_NAME` setting.

## How to work with T
- Build in thin vertical slices: model → API → UI, one feature end to end.
- T supplies expected behavior as concrete test cases; write tests first for the core.
- T reviews test assertions more closely than implementation — make them readable.
- **Don't add scope.** No "while I was in here" changes, no speculative abstractions.
- Run the code, tests, and linters. "Looks right" is not verification.
- For PM docs (specs, decision log entries, prioritization): **T writes first, Claude critiques.** Claude may draft interview guides, synthesize notes, and argue against plans.
- Simulated users are never evidence.
- Be direct; no sugarcoating.
- When a new decision is made, append it to `docs/decision-log.md` and update this file if it changes a rule.

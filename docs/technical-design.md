# Baking App — Technical Design

Last updated: 2026-10-14. Reasons and rejected alternatives for each choice: `decision-log.md`.

## 1. Architecture
```
Browser (React SPA, TypeScript)
   │  same origin, session cookie + CSRF
   ▼
Django (DRF API + serves built SPA via WhiteNoise)  ──►  Anthropic API (recipe parsing)
   │                                                ──►  Cloudflare R2 (photos, signed URLs)
   ▼
PostgreSQL (managed, Render)
Sentry (errors, both tiers) · PostHog (product analytics) · uptime monitor
```
- One Render web service, one managed Postgres. Deploy on green `main` after CI.
- Environments: local (Docker Compose Postgres) + production. Add staging when real users arrive.
- Secrets: Render env vars in prod, `.env` locally (gitignored).
- AI parsing is a synchronous request in v1 (show progress). Background queue (Celery/Redis) only if latency or bulk import demands it.

## 2. Stack
| Layer | Choice |
|---|---|
| Backend | Python, Django, Django REST Framework |
| Database | PostgreSQL (pgvector later if semantic search is needed); raw SQL allowed for reporting queries |
| Frontend build | Vite |
| Frontend | TypeScript, React, React Router (library mode) |
| Server state | TanStack Query |
| Forms | React Hook Form + Zod (UX only; DRF serializers are the source of truth) |
| UI | shadcn/ui + Tailwind (Mantine was the close second) |
| Charts | Recharts |
| API types | drf-spectacular → openapi-typescript (generated) |
| AI | Anthropic SDK + Pydantic; thin internal `RecipeParser` interface |
| File storage | Cloudflare R2 via django-storages S3 backend; Pillow resize on upload |
| Auth | Django sessions + CSRF |
| Errors | Sentry (Django + React; releases tagged with git SHA; source maps uploaded) |
| Logging | Structured JSON to stdout |
| Analytics | PostHog |
| CI | GitHub Actions: pytest, mypy, ruff, tsc, ESLint |
| Quality | Playwright (few E2E flows) |

## 3. Data model (entities)
All tenant-owned tables carry `organization_id` and are accessed via the org-scoped manager.

**Tenancy**
- `Organization`
- `Membership` (user, organization, role: owner | member)
- `OrgSettings` (display_units: metric | imperial, labor_rate_per_hour, overhead_pct, currency — single)

**Supply**
- `Supplier`
- `Ingredient` (name, kind: ingredient | packaging, density_g_per_ml nullable, grams_per_each nullable, allergens, may_contain)
- `Purchase` — **append-only; each purchase is a lot.** supplier, ingredient, quantity_entered, purchase_unit, quantity_base, total_price, unit_cost_base (derived), purchased_at, expires_at (optional). Creates a `purchased` ledger entry. **Purchases are the price history** — no separate price table.

**Recipes**
- `Recipe` (name, tags, current_version, draft)
- `RecipeVersion` — **immutable.** version_number, change_note (required), yield_quantity_base, product link, shelf_life, notes, hero_photo, created_by, created_at
- `RecipeLine` (version, ingredient XOR sub_recipe, quantity_entered, unit_entered, quantity_base) — DB check constraint for XOR
- `RecipeStep` (version, order, description, duration_minutes, mode: active | passive, scaling: fixed | linear, temperature optional)

**Products**
- `Product` (recipe, name, measure: count | weight, base_unit_name e.g. "slice")
- `ProductVersion` — new version when portion definition changes
- `SellUnit` (product_version, name e.g. "whole", base_units_per_sell_unit e.g. 12, list_price, packaging lines)

**Production**
- `Batch` — append-only. recipe_version, scale_factor, expected_yield_base, actual_yield_base, made_by, made_at, use_by, actual_active_minutes (optional), cost_total, cost_breakdown (ingredients/labor/packaging/overhead), cost_is_estimated, plan_item (optional). Each batch is a finished-goods lot.
- `ProductionPlan`, `PlanItem` (sell_unit, quantity, due_at)

**Inventory ledger**
- `LedgerEntry` — **append-only.** item (ingredient XOR product), lot (purchase XOR batch), entry_type, quantity_base (signed), unit_cost, created_by, created_at, related_batch (for produced/consumed), sale fields (sell_unit, sell_quantity, sale_price) for `sold`, waste_reason (expired | cut_loss | damaged) for `wasted`, adjustment_reason (count | shrinkage), reverses (FK self).
- **Entry types:** purchased · produced · consumed · sold · wasted · given_away · adjustment · reversal
- Current stock = SUM(quantity_base) per item (and per lot).

**AI**
- `RecipeParse` (input_type: text | image, input_ref, model, prompt_version, raw_output, validated_output, status, input_tokens, output_tokens, cost, created_by, resulting_recipe)

## 4. Business rules
**Units**
- Store g, ml, each. Display per `OrgSettings.display_units`.
- Volume → weight: `density_g_per_ml`. Each → weight: `grams_per_each`. Missing → raise `MissingConversionError`; UI prompts the user. Never guess.
- Preload densities for common ingredients.

**Costing**
- Live recipe cost: latest purchase unit cost per ingredient.
- Batch snapshot: FIFO across lots (oldest `purchased_at` / `made_at` first). Shortfall past available stock → latest price, `cost_is_estimated = true`.
- Sub-recipes: always latest version; recursive rollup; cycles rejected on save (graph check).
- Labor: Σ(active step minutes, linear steps × scale factor, fixed steps unscaled) × labor_rate_per_hour / 60.
- Packaging: per sell unit.
- Overhead: overhead_pct × (ingredients + labor + packaging).
- Cost per base unit = batch cost ÷ actual base-unit yield; per sell unit = × multiple.

**Inventory**
- Logging a batch: `produced` +actual yield (product, new lot); `consumed` −scaled quantities for ingredients and sub-recipe products (FIFO).
- Negative stock allowed; API returns a warning flag.
- Corrections: `reversal` entry pointing at the original. No UPDATE/DELETE on append-only tables.
- Portion changes create a new ProductVersion; existing stock keeps its original definition.

**Versioning**
- Draft autosaves; "save as new version" requires a change note and freezes it.

**Allergens**
- Union through all lines, recursively through sub-recipes; "may contain" propagates the same way.

**Production planning**
- needed_base = Σ(plan qty × sell multiple) − on-hand finished stock; batches = ceil(needed_base ÷ yield_base) → scale factor; recurse into sub-recipes; aggregate ingredient needs; compare with stock → shortfall list; backward schedule from due_at using step durations.

## 5. AI parsing pipeline
1. Input stored (text, or image resized and uploaded to R2).
2. Call Claude with structured output (JSON schema / tool use); image input uses vision directly (no separate OCR).
3. Validate with Pydantic. Failure → one retry including the validation error → else partial result + manual entry.
4. Match ingredient names to the org catalog (normalized + fuzzy match); flag unknowns and low confidence.
5. Return to the review screen. User confirms → draft recipe.
6. Record model, prompt_version, tokens, cost on `RecipeParse`.
- Model is a config setting. Default to a mid-tier model; test a cheaper tier against evals; choose by eval score vs cost.
- Prompts are versioned files in the repo.
- Per-org daily parse limit (cost control and abuse prevention).
- Evals: 30–50 real messy recipes with expected output; also score a rule-based parser as a baseline. CI runs against recorded fixtures; live evals run on demand.

## 6. Testing strategy
- **Strict TDD:** unit/density conversion, scaling, step-time scaling, cost rollup incl. sub-recipes, cycle detection, margins, ledger sums, FIFO, negative-stock estimation, sell-unit math, plan math, org isolation.
- **Integration:** pytest + Django test client on real Postgres.
- **E2E:** Playwright — create recipe → scale → see cost; log batch; log sale.
- **AI:** evals as above.
- **CI:** all checks on every push; deploy only on green `main`.

## 7. Frontend conventions
- Server data only through TanStack Query; invalidate stock/dashboard queries after ledger writes.
- Large dynamic forms via React Hook Form `useFieldArray`; Zod schemas define client types.
- API types generated from OpenAPI — regenerate on backend change; the frontend must fail to compile on drift.
- Mobile-first layouts; touch targets ≥ 48px; numeric keypad input modes; Wake Lock in cook mode; PWA manifest.

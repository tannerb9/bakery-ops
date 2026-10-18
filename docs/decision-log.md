# Baking App — Decision Log

Format: **Decision** · Why · Rejected alternatives (and why). Append new entries; don't rewrite old ones. Mark a decision as superseded if it changes.
All entries below: 2026-10-14 unless noted.

---

## Goals and process

**D1. PM experience is the primary goal; AI engineering is the differentiator; food business readiness is secondary.**
Why: matches T's job target (PM or a credible path to it). Engineering skill grows anyway from building; PM skill only grows if time is protected for it.
Rejected: equal-weight goals — they pull scope in opposite directions (AI learning adds, PM cuts) and the project becomes engineering by default.

**D2. Research before building; the feature list is a hypothesis.**
Why: interviewers ask who used it, what you learned, and what you cut. Building straight from the base list produces no PM story.
Rejected: (a) building the base app first — no evidence for decisions; (b) building only what users request — order-taking, not product management.

**D3. Interviews (weeks 1–3) run in parallel with foundation work.**
Why: the recipe/costing core and tenancy are needed by almost any version of the app, so they're low-risk to build early.

**D4. T writes PM docs; Claude critiques.** Simulated users are never evidence.
Why: if Claude writes specs, T can't defend them in interviews and learns nothing.

## Stack

**D5. Backend: Python + Django.**
Why: Python is the main language of the AI ecosystem; Django's ORM, migrations, auth and admin fit relational CRUD; T already knows it.
Rejected: FastAPI — modern and in demand, but loses the admin and batteries; all-TypeScript (Next.js) — cleaner single language, weaker for evals/data/forecasting work.

**D6. Frontend: TypeScript + React.**
Why: TypeScript is expected on modern roles; types catch unit/quantity bugs. Upgrade from T's plain JS.

**D7. Database: PostgreSQL.**
Why: data is heavily relational (recipes ↔ ingredients ↔ suppliers ↔ lots); append-only history is natural; pgvector available later.
Rejected: MongoDB — manual joins and consistency problems for relational data.

**D8. Responsive web app, mobile-first.**
Rejected: native Swift/Kotlin — unnecessary; React Native only if proven needed. Go/Rust/microservices — scale problems that don't exist.

**D9. API: Django REST Framework.**
Rejected: GraphQL — overkill for this app; adds tooling for little gain.

## Frontend tooling (gap 17)

**D10. Vite.**
Why: fast, minimal config, clean SPA that talks to Django; Django owns data/auth, React owns UI.
Rejected: Next.js — a second server framework overlapping Django; SSR/SEO not needed behind login. React Router framework mode/Remix — same issue. Create React App — deprecated. Hand-rolled Webpack — config time sink. Django templates + HTMX — legitimate, but TS/React is a skill goal and the editor/diff/planning UIs are interactive.

**D11. TanStack Query.**
Why: caching, retries, loading/error state, and especially invalidation — one batch log changes stock, costs and dashboard.
Rejected: useEffect + fetch — reinvents caching and race handling badly. Redux Toolkit + RTK Query — Redux boilerplate for client state the app barely has. SWR — weaker mutation/invalidation. Apollo — GraphQL only.

**D12. React Hook Form + Zod.**
Why: performant large dynamic forms (`useFieldArray` for ingredient rows); Zod gives schema and inferred types in one place. Server validation (DRF) remains the source of truth.
Rejected: Formik — barely maintained, re-renders whole form. Plain useState — painful at recipe-editor scale. TanStack Form — good but younger, fewer integrations (revisit later). Yup — weaker TS inference. Valibot — smaller ecosystem, bundle size doesn't matter here.

**D13. shadcn/ui + Tailwind.**
Why: accessible Radix primitives, code copied in and owned (needed for kitchen-sized touch targets), widely used.
Rejected: Mantine — close second, faster to working UI, less ownership. MUI — heavy, Material look, hard to customize deeply. Chakra — v3 churn. Ant Design — dense enterprise look, big bundle. Hand-built Tailwind — slow and easy to break accessibility.

**D14. React Router (library mode).**
Rejected: TanStack Router — better type safety, less common. Either is defensible.

**D15. Generated API types: drf-spectacular → openapi-typescript.**
Why: backend changes break the frontend build instead of production. Rejected: hand-written types — drift within weeks.

## Data model and business rules

**D16. DECIMAL for money and quantities.** Rejected: floats — rounding errors in costs.

**D17. Multi-tenant from day one** (Organization + Membership with roles; org-scoped manager; isolation test).
Why: retrofitting tenancy touches every table. Rejected: single-user — cheaper now, painful migration later.

**D18. Store metric (g, ml, each); display metric or imperial per org.**

**D19. Volume→weight via per-ingredient density; each→weight via grams per item. Missing value → fail loudly and ask.**
Why: a cup of flour (~120 g) ≠ a cup of sugar (~200 g). Rejected: guessing defaults — silent cost errors.

**D20. Live costing = latest purchase price; batch snapshots = FIFO lot cost.**
Why: live view should reflect today's prices; history should reflect what was actually paid.
Rejected: weighted average — smooths away real price signals and is harder to explain.

**D21. Purchase log; each purchase is a lot and doubles as price history.**
Rejected: separate price-history table — duplicate source of truth.

**D22. Inventory is a single append-only ledger.**
Entry types: purchased, produced, consumed, sold, wasted, given_away, adjustment, reversal. Stock = sum of entries.
Why: audit trail, matches append-only convention, enables traceability later. Rejected: mutable running totals — no history, untraceable errors.

**D23. Corrections via reversal entries.** Rejected: edits/deletes — break the audit trail.

**D24. Adjustment entries for physical counts and shrinkage.**

**D25. Negative stock allowed with a warning; shortfall costed at latest price and flagged estimated.**
Rejected: blocking — frustrates real users; the negative balance is useful data.

**D26. Batch logging with finished-goods inventory.** Batch stores recipe version, scale, expected/actual yield, cost snapshot, who/when, use-by. Proposed by T.

**D27. Outflow reasons: sold, expired/wasted, given away, used in another recipe.** (T)

**D28. Stock tracked per batch/lot with FIFO consumption.** Why: use-by dates differ per batch; lot traceability comes nearly free.

**D29. Sub-recipes supported; always use the latest version; auto-deducted when the parent batch is logged; recursive cost rollup; cycles rejected.** (T chose latest version.)
Why latest: the batch cost snapshot already preserves history. Rejected: pinned versions — stale parent recipes. Manual sub-recipe deduction — data drifts within a week.

**D30. Sales record sell unit, quantity and price.** (T) Why: real margins. Risk: friction — validate in interviews.

**D31. Partial units: integer base units + named sell units (Option C).**
Rejected: Option A, fractional quantities — 1/12 repeating decimals drift, no per-slice price. Option B, separate products + "cut" events — extra user step that gets forgotten.
Portion changes create a new product version. Cutting losses logged as wasted.

**D32. Recipe versions only on explicit "save as new version" with a required change note; autosaved draft between.**
Rejected: version on every edit — typo fixes become versions.

**D33. Allergens roll up through sub-recipes; "may contain" supported.**

## Tier 2 product specs

**D34. Time model: ordered steps with active/passive mode and fixed/linear scaling; labor = active minutes × org hourly rate.**
Why: double batch ≠ double oven time. Rejected: single total-time field — can't scale or cost labor.

**D35. Packaging attached to sell units; overhead as org-level % of direct costs (v1), moving to monthly overhead ÷ volume later; always show cost breakdown.**
Rejected: overhead per batch — arbitrary; hidden single total — hides assumptions.

**D36. Recipe content: ingredients, steps, yield, shelf life, notes, tags, hero photo, derived allergens; diff view with cost delta.**

**D37. Production planning v1: batches needed → sub-recipe batches → shortfall shopping list → backward timeline → "start batch".** Deferred: equipment capacity, staffing, multi-day plans.

**D38. Reporting: dashboard (action list + 4 KPI tiles) and question-driven reports; every number drills down to ledger rows; estimates flagged. v1 ships dashboard, profitability table, cost-over-time chart only.** Charts via Recharts.

## Gap 18 — AI parsing flow

**D39. Claude with structured output + Pydantic; vision handles photos directly; mandatory review screen; saves as draft; retry once then manual fallback; synchronous in v1; model is config chosen by eval score vs cost; prompts versioned; model/prompt/tokens/cost logged per parse; per-org daily limit; rule-based parser as eval baseline.**
Why: parse errors flow straight into money calculations, so a human must confirm. Logging model + prompt version makes regressions traceable.
Rejected:
- Rule-based parsers only (e.g. ingredient-parser libraries) — cheap and deterministic, but break on messy formats and can't read photos. Kept as eval baseline.
- Separate OCR (Tesseract/Textract) + LLM — extra moving part; modern vision models read photos and handwriting directly.
- Auto-save without review — silent cost corruption.
- LangChain/agent frameworks — abstraction over one API call; hides what T is trying to learn.
- Celery/Redis queue now — infra before it's needed.
- Hard-coding a provider — keep a thin interface so evals can compare.

## Gap 19 — File storage

**D40. Cloudflare R2 via django-storages (S3 API); private bucket with signed URLs; resize/compress on upload with Pillow; upload through Django in v1.**
Why: S3-compatible (skills transfer to AWS), no egress fees, generous free tier; recipes are business secrets so files stay private.
Rejected: AWS S3 — industry standard but egress fees and IAM setup; easy to switch later via the same API. Local server disk — wiped on redeploy on Render. Postgres blobs — bloats DB and backups. Cloudinary — nice transforms, pricing/lock-in. Supabase Storage — ties you to Supabase.

## Gap 20 — Hosting and deployment

**D41. Render: one web service (Django serves API + built SPA via WhiteNoise, same origin) + managed Postgres; deploy on green `main`; local Docker Compose; staging added when real users arrive; secrets in env vars; budget for a paid database tier with backups once real users exist.**
Why same origin: Django session auth + CSRF works without CORS or token handling.
Rejected: Railway — similar; usage-based pricing less predictable. Fly.io — more control, more ops. Heroku — pricier, stagnant. AWS (ECS/Elastic Beanstalk) — résumé value but heavy ops at the wrong time. Vercel frontend + separate backend — split origins add CORS/auth complexity; Vercel shines with Next.js, which we didn't pick. Self-managed VPS — cheapest, but you own patching and security.

**D42. Auth: Django sessions + CSRF.**
Rejected: JWT — token storage risks and refresh logic with no benefit on a single origin.

## Gap 21 — Error tracking and logging

**D43. Sentry free tier on Django and React (releases tagged by git SHA, source maps uploaded); structured JSON logs to stdout; free uptime monitor.**
Rejected: logs only — you learn about errors from users. Rollbar/Bugsnag — fine, smaller ecosystem. Datadog/New Relic — overkill and expensive. GlitchTip self-hosted — Sentry-compatible, but you host it. PostHog error tracking — would consolidate tools, but less mature than Sentry.

## Gap 22 — Legal basics

**D44. Before first external user: privacy policy, terms (users own their recipes/data), AI-provider disclosure, CSV export, org/account deletion. Use a generator template now; lawyer review only if it becomes a real business.**
Rejected: skipping — acceptable for friends, not strangers, and weak PM practice. Hiring a lawyer now — premature cost. Copying another app's policy — copyright issues and doesn't match your data flows.
Note: Claude is not a lawyer; this is a starting point, not legal advice.

## Gap 23 — Kitchen-ready design

**D45. ≥ 48px targets, bottom thumb-zone actions, log batch in ≤ 3 taps with pre-filled defaults, steppers/numeric keypad, high contrast, WCAG AA, cook-mode Wake Lock, undo toast, installable PWA. No offline mode in v1; offline queue for batch/sales logging only if interviews show the need.**
Rejected: desktop-first — bakers aren't at desks. Full offline-first sync (local-first/CRDT) — conflict resolution with a ledger is hard; don't build speculatively. Voice input — interesting hands-free AI feature, premature (parked in Later).

## Naming and repo (2026-10-17)

**D46. Repo name: `bakery-ops`. Brand name deferred** (working favorite: Proof; fallback: Crumbtrail) until interviews settle the target segment.
Why: descriptive, brand-neutral, and GitHub redirects renamed repos, so renaming later is cheap.
Rejected: picking the brand now — the right tone depends on whether users are home bakers or commercial bakeries; "___Cost" names — crowded (BakeCost, CakeCost, BatchCost exist); "Mise" variants — meez already owns that pun.

**D47. Neutral internal naming; brand lives in one setting.**
Django project `config/`; apps by domain (`organizations`, `recipes`, `inventory`, `production`, `parsing`); frontend package `web`; every user-facing brand string reads from `APP_NAME`.
Why: rebranding becomes a one-setting change. Rejected: brand name in module/package names — forces a codebase-wide rename later.

## Foundation tooling (2026-10-17)

**D48. Python dependencies managed with uv (`pyproject.toml` + `uv.lock`).**
Why: fast, one tool for virtualenv + locking, CI installs exactly the locked versions.
Rejected: pip + requirements.txt — no real lockfile; Poetry — slower, more config, losing ground to uv.

**D49. Keep ESLint (D-stack decision) even though the current Vite template ships oxlint.**
Why: ESLint has the React Hooks rules and typescript-eslint strict rules; it's what employers' codebases use.
Rejected: oxlint — much faster, but a younger rule set. Revisit if lint time ever matters.

**D50. Dev server proxies `/api` and `/admin` to Django** so local dev is single-origin like production (needed for session auth + CSRF).

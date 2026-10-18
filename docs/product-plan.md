# Baking App — Product Plan

Last updated: 2026-10-14 · Owner: T (Tanner Brainard)

## 1. Goals and positioning
- **Primary:** gain real product management experience — discovery, scoping, specs, metrics, iteration with real users.
- **Differentiator:** AI engineering skill (recipe parsing, evals, structured output).
- **Secondary:** a tool usable if T starts a food company. Don't build for a hypothetical company.
- **Positioning story:** "engineer who builds AI products and makes product decisions" (technical PM / AI PM / product engineer).
- **Flip condition:** if software engineering roles become the main target, shift emphasis to architecture, testing and AI depth. Same project.
- **Tie-breaker:** not supported by user research → not built. Curiosity features go on a separate branch.
- **Biweekly check:** did I talk to a user, write a spec, or look at metrics? If only "wrote code," I've drifted.
- T's own bakery experience (Shanghai) counts as one data point, not as validation.

## 2. Process
1. **Weeks 1–3:** 8–10 baker interviews **in parallel with** foundation work (repo, CI, org/tenant model, core data model, costing engine with TDD).
2. Hold all other features until interviews finish.
3. **After interviews:** problem statement, 2–3 personas, cut v1 to the smallest useful version, record what changed from this plan and why.
4. Ship to 5–15 real active users; observe, collect feedback, iterate, document changes.
5. **Final deliverable:** case study — problem found, who I talked to, what I cut and why, what shipped, metrics, what I learned.

**PM artifacts to maintain:** one-page spec per feature (problem, user, success metrics, non-goals, open questions) · decision log · RICE or impact/effort prioritization · Now/Next/Later roadmap · release notes.

**Interview rules:** ask about past behavior, not hypotheticals. Recruit home bakers, cottage-food sellers, small bakery owners, caterers (NYC).

**Interview questions collected so far:**
- How did you figure out what to charge for your last order?
- Walk me through what happens after you finish a batch. Do you write anything down?
- How do you know what's left at the end of the day?
- What happens to what doesn't sell?
- Do you sell the same item in multiple sizes? How do you price a slice vs a whole cake?
- How do you currently know which products make you money?
- What's the Wi-Fi / phone situation in your kitchen? (offline need)
- Would you record the price on every sale? (friction check)

## 3. Metrics (placeholders — finalize after interviews)
- **North star:** recipes costed per active user per week.
- **Activation:** first recipe costed within 10 minutes of signup.
- **Instrumentation:** PostHog installed **before** launch.

## 4. v1 hypothesis (to be cut after interviews)
Recipes with version history · ingredient costing · time calculation · purchase log + raw-ingredient inventory · batch scaling and production planning · pricing and margin calculator · allergen roll-up · batch logging with finished-goods inventory and outflows · **AI recipe parsing** (first AI feature).

**Likely survivor regardless of interviews:** recipe + ingredient + unit conversion + costing core.

**Later:** order management, waste/yield analytics, lot traceability, food safety logs, AI ingredient substitution, natural-language queries, demand forecasting (needs real sales data), voice input in kitchen mode.
**Out of scope:** labor scheduling, POS/accounting integrations, native mobile apps.

## 5. Feature specs (current recommendations)

### 5.1 Batch logging and finished goods
- A batch records: recipe version, scale factor, expected and actual yield (base units), FIFO cost snapshot, made by, made at, use-by date (from shelf life), optional actual active minutes.
- Logging a batch: finished goods **+actual yield**; raw ingredients **−scaled amounts**; sub-recipe products **−consumed** automatically.
- **Outflows:** sold, expired/wasted (incl. cutting loss), given away, used in another recipe (automatic).
- **Sales record sell unit, quantity, and price** — real margins, not estimates.
- Stock is tracked per batch; consumption is FIFO.
- UX: after logging, toast with **Undo** (creates a reversal entry).

### 5.2 Products and partial units
- Count-based products store stock as integer smallest portions; **sell units** are named multiples. Example: chocolate cake base unit = slice; sell units: whole = 12, half = 6, slice = 1. Brownies: tray = 24, box of 6 = 6, piece = 1.
- Weight-based products (pastry cream, granola) store DECIMAL grams.
- Cost per base unit = batch cost ÷ base-unit yield; cost per sell unit = × multiple.
- Changing portion size (12 → 10 slices) = new product version.
- Insight unlocked: margin per slice vs per whole cake.

### 5.3 Time model
- Recipe = ordered steps. Each step: duration, **active** (hands-on) or **passive** (proof/bake/chill), scaling rule **fixed** (bake, proof) or **linear** (shape, portion), optional temperature/notes.
- Total time = sum of steps (parallel steps deferred).
- **Labor cost = active minutes × org hourly rate.** Passive time has no labor cost.
- Batch log captures optional actual active minutes for estimate-vs-actual.

### 5.4 Overhead and packaging
- **Packaging attaches to the sell unit**, not the recipe (cake box vs slice clamshell). Packaging items are purchased and costed like ingredients.
- **Overhead v1:** org-level percentage markup on direct costs (ingredients + labor + packaging).
- **Overhead later:** monthly overhead ÷ monthly production volume (from batch log).
- Always show the breakdown: ingredients / labor / packaging / overhead, with estimated parts marked.

### 5.5 Recipe content and versioning
- Fields: ingredient lines (incl. sub-recipes), ordered steps, yield + base unit, shelf life, notes, tags, one hero photo (step photos later), derived allergens + "may contain".
- Saved versions are immutable; edits go to an autosaved draft; **"save as new version" requires a change note** (e.g. "Cut butter 10% — too greasy").
- **Diff view** between any two versions: ingredient adds/removes/quantity changes highlighted, step text diff, **cost-per-unit delta**, yield delta (from batch data).

### 5.6 Allergens
- Allergens tagged on ingredients, rolled up through sub-recipes to every product.
- "May contain" (cross-contact) warnings supported.

### 5.7 Production planning (minimal v1)
Input: plan items (product, sell-unit quantity, due date/time).
Output:
1. Batches needed: convert to base units, subtract on-hand finished stock, round up to whole batches → scale factor.
2. Sub-recipe batches needed, recursively.
3. **Ingredient pull list vs current stock → shortfall shopping list.**
4. Backward timeline from due date using step times ("Start croissant dough Wed 2pm").
5. "Start batch" → pre-filled batch log.
Deferred: oven/equipment capacity, staff assignment, multi-day overlapping plans.

### 5.8 Reporting
Principle: every view answers a question a baker asks; actionable first.
- **Home dashboard (mobile-first):** action list (expiring soon FIFO, negative stock, shortfalls for upcoming plans) + 4 KPI tiles (revenue this week, gross margin %, waste rate, units produced) with week-over-week change.
- **Reports:**
  - Which products make money? → table sorted by gross profit (units sold, revenue, cost/unit, margin %, sparkline).
  - How has this recipe's cost changed? → line chart of cost per unit with **annotations for version changes and price changes** (signature chart).
  - What's driving cost increases? → table of biggest ingredient price movers + affected recipes.
  - Where does product go? → stacked bar by week: sold / expired / given away.
  - Slice vs whole? → bar chart of margin per base unit by sell unit.
  - Yield on target? → expected vs actual yield by recipe version.
- Rules: every number drills down to its ledger rows; estimated values visibly flagged; default range last 30 days; on mobile, tiles and lists before charts.
- **v1 ships only:** dashboard, product profitability table, cost-over-time chart. Others when users ask.

### 5.9 AI recipe parsing
- Input: pasted text or photo → Claude (vision for photos) with structured output → Pydantic validation → match to org's ingredient catalog; unknown or low-confidence items flagged.
- **Mandatory review screen:** original vs parsed side by side, editable; unmatched ingredients and missing densities highlighted.
- Confirm → saves as a **draft** recipe (not a version).
- Failure: one retry with the validation error; then fall back to manual entry pre-filled with whatever parsed. Never block the user.
- Quality bar: decided by eval accuracy; ship threshold to be set after baseline run.

### 5.10 Kitchen-ready design
- Touch targets ≥ 48px; primary actions in thumb reach at the bottom.
- **Log batch in ≤ 3 taps** from home; defaults pre-filled (last scale, expected yield).
- +/− steppers and numeric keypad inputs instead of full keyboards.
- High contrast, large type, legible in bright light; WCAG AA.
- **Cook mode** keeps the screen awake (Wake Lock API).
- Undo via toast (reversal entry).
- Installable PWA (home-screen icon). **No offline mode in v1**; if interviews show bad Wi-Fi, add an offline queue for batch/sales logging only.

### 5.11 Legal basics (before first external user)
Privacy policy, terms of service (users own their recipes/data), disclosure that recipe text/photos go to a third-party AI provider, data export (CSV), org/account deletion. Generator template now; lawyer review only if it becomes a real business.

## 6. Open questions
**PM**
- Target segment: home bakers vs cottage-food sellers vs small commercial bakeries (interviews decide).
- Interview guide and recruiting plan — not written yet (T writes, Claude critiques).
- Final success metrics.
- Timeline and milestones.

**Validate in interviews**
- Is batch logging worth the overhead for occasional home bakers?
- Will users record price on every sale?
- Is offline support needed?
- Which AI feature matters most (parsing vs pricing help)?
- Is the sell-unit model right for how they sell?

**Tier 3 (can wait)**
- Nutrition data source (USDA FoodData Central — may also seed densities).
- Raw-ingredient expiry tracking (purchases are lots already; expiry optional).
- Sales channel / customer on sales (retail, wholesale, market).
- Taxes, discounts, multi-currency (assume single currency, pre-tax).
- CSV import/export of recipes.
- Timezone handling for use-by dates and reports.

## 7. Next steps
1. T writes the interview guide; Claude critiques.
2. Recruit 8–10 interviewees.
3. Set up repo, CI, Docker Compose, Django project with org model + isolation test.
4. TDD the unit conversion + costing engine.

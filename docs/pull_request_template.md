## Why
<!-- The problem or decision this PR addresses. Link decision-log entries (e.g. D60). -->

## What changed
-

## How it was tested
- Tests added/changed:
- Mutation-checked (what was broken on purpose, and did the suite catch it?):

## Decisions
<!-- New or changed entries in docs/decision-log.md. Label origin honestly: T decided / Claude recommended, T approved / Claude's reasoning. -->

---

## Review (T)
**Verdict:** Approve / Request changes / Comment

**Matches the request?** yes / no —
**Tests reviewed:** what I checked, what's missing —

**Risks checked**
- [ ] Money and quantities use `Decimal`/`Fraction`, never `float`
- [ ] New bakery data uses `OrgOwnedModel` + `OrgScopedViewSet`
- [ ] Append-only tables are never updated or deleted
- [ ] Missing data raises instead of guessing
- [ ] Migration included if a model changed; no data loss
- [ ] Docs updated if a rule changed; every "T decided" is really mine
- [ ] CI green

**Blocking:**
-

**Questions:**
-

**Nits:**
-

**Praise:**
-

**Learned:**
-

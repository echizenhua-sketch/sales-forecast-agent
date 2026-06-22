# Static Frontend And AI Detail Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the static HTML pages the only frontend served at `http://127.0.0.1:4173/`, and make `/api/chat` include real SKU detail rows from the database in AI context.

**Architecture:** Vite remains only the static file server for `web/*.html`; `web/index.html` redirects to `login-v2.html` and no longer mounts React. The backend `/api/chat` continues to serve the static pages, but enriches `context` with `TaskSummary` and prioritized `SkuForecastDetail` rows before invoking `AIService`.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Vite static serving, plain HTML/JavaScript.

---

### Task 1: Static Frontend Entry

**Files:**
- Modify: `web/index.html`
- Modify: `web/package.json`
- Modify: `web/tests/smoke.spec.ts`

- [ ] Write/adjust Playwright smoke so root route expects login-v2 static UI.
- [ ] Change `web/index.html` to redirect to `/login-v2.html` without loading `/src/main.tsx`.
- [ ] Keep Vite dev/build usable as static server.
- [ ] Run `npm run build --prefix web` and `npx --prefix web playwright test`.

### Task 2: AI SKU Detail Context

**Files:**
- Modify: `app/api/tasks.py`
- Modify: `app/services/ai_service.py`
- Modify: `tests/test_ai_service.py`
- Add or modify API test for `/api/chat` context behavior.

- [ ] Add failing tests proving `/api/chat` passes `sku_details` from `SkuForecastDetail` to `AIService`.
- [ ] Query top risk/shortage SKU rows by task, capped to 20 rows.
- [ ] If the user question includes a SKU code, include that exact row even if it is outside the top 20.
- [ ] Update AI system prompt to include real SKU detail rows from context.
- [ ] Run `python -m pytest -q`.

### Task 3: Live Verification

**Files:**
- No committed artifacts expected.

- [ ] Restart backend on `127.0.0.1:8000`.
- [ ] Verify `GET http://127.0.0.1:4173/` lands on static login.
- [ ] Verify login flow reaches `dashboard-v2.html`.
- [ ] Verify `/api/chat` returns `llm_generate` and can reference SKU details when task data exists.

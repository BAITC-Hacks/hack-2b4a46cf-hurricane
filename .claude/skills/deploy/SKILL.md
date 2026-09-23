---
name: deploy
description: Deploy the backend (app/) to Railway with `railway up`, wait for /health, and read logs if it fails. Use when asked to deploy, ship, roll out, "задеплой", "выкати", "залей на railway", or to check deploy logs. The project has a single shared `production` environment and no GitHub autodeploy.
allowed-tools: Bash(railway *), Bash(curl *), Read
---

Single source of truth: `DEPLOYMENT.md` in the repo root. Read it before the first deploy in a session.

## Preflight (stop and tell the user if any step fails)

1. `railway whoami` — CLI installed and logged in. If not: install and login per DEPLOYMENT.md, section "Требования".
2. `railway status` from `app/` — project, service and environment are linked.
3. `production` is the only environment and it is shared by the whole team — a deploy replaces what everyone sees. Say out loud what is about to ship and confirm with the user before the first deploy of a session.

## Deploy

1. In `app/`: `uv run ruff check . && uv run ruff format --check .`. Red output → fix first, do not deploy.
2. `railway up --detach` from `app/`.
3. `railway domain` to get the URL. Poll `curl -fsS <url>/health` up to ~2 minutes (Railway switches traffic only after the healthcheck passes).
4. Report: URL, deploy status, one line on what changed.

## If it fails

- Build failed: `railway logs --build`, fix Dockerfile/deps, redeploy.
- Crashed at start: `railway logs --deployment`. Usual causes: missing variable, `DATABASE_URL` without `+asyncpg`, migration error from `preDeployCommand`.
- Read `railway variables` only to check names. Never print values into chat or files.

## Never

- Change variables or delete anything without the user asking. Deploying is the point; destructive changes are not.
- Delete services, environments or volumes.

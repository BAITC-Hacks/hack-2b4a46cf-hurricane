---
name: setup
description: First-time local setup after cloning this repo. Checks tools (git, Docker/Podman Compose, uv, Node 22, yarn 1, Railway CLI), creates .env, enables git hooks, runs docker compose, waits for /health, and connects Railway CLI + MCP. Use when a teammate asks to set up, install, onboard, start locally, "настрой проект", "подними локально", "быстрый старт", "как запустить", or when the project has never been run on this machine.
allowed-tools: Bash, Read, Glob
---

Goal: a teammate on macOS or Windows goes from `git clone` to a working app on http://localhost:5173 in under 10 minutes. Follow README section «Запуск» and AGENTS.md; this skill only automates them. Windows users may run inside PowerShell: use `Copy-Item` instead of `cp`, and never write shell scripts into the repo (AGENTS.md rule).

## 0. Fast path: `python dev.py`

Run `python dev.py` from the repo root first (`python3` on macOS if `python` is missing). It does sections 1–4 below by itself: tools table, `git config core.hooksPath`, `.env` from the example with free ports picked automatically, `compose up --build -d`, waiting for `/health`, and prints the URLs. Read its output and continue from section 5 (verify). Fall back to the manual steps only if the script exits with an error; its last lines say which step failed. Other subcommands: `python dev.py down`, `python dev.py logs app`, `python dev.py status`, `python dev.py check`.

## 1. Tools check

Run each and report a table: tool, found version or «нет», required.

| Tool | Command | Required |
|---|---|---|
| git | `git --version` | yes |
| Compose | `docker compose version`, fallback `podman compose version` | yes, Compose v2.24+ (`env_file: required: false` needs it) |
| Node | `node --version` | 22+, only for IDE types/lint and `yarn dev` without Docker |
| yarn 1 | `yarn --version` | 1.22.x, same scope as Node |
| uv | `uv --version` | only for `uv run ruff` and dev without Docker |
| Railway CLI | `railway whoami` | yes for deploys, see DEPLOYMENT.md |

If a tool is missing, show the install command for the user's OS and ask before installing anything global:
- macOS: `brew install --cask docker` (or Podman Desktop), `brew install uv node railway`, `npm i -g yarn@1`
- Windows: `winget install Docker.DockerDesktop`, `winget install astral-sh.uv`, `winget install OpenJS.NodeJS.LTS`, `npm i -g yarn@1 @railway/cli`

If `podman` is the engine, use `podman compose` everywhere below and make sure the Podman machine is running (`podman machine start`). On this repo `docker compose` and `podman compose` are interchangeable.

## 2. Repo hygiene

- `git config core.hooksPath .githooks` (required: the commit-msg hook rejects AI co-authorship lines).
- Confirm `git status` is clean and the branch is `main`.

## 3. `.env`

- If `.env` is missing, copy `.env.example` to `.env`.
- Tell the user to open `.env` in their editor and fill `OPENAI_API_KEY` (ask the captain for the team's value). **Never ask the user to paste secrets into the chat and never print `.env` contents.**
- Everything else has working defaults. If ports 8000, 5173 or 5432 are busy on the machine, set `APP_PORT`, `UI_PORT`, `DB_PORT` in `.env`. Check with `lsof -i :8000` (macOS) or `netstat -ano | findstr :8000` (Windows).
- Stop here and wait for the user to confirm the key is in place before starting containers; without `OPENAI_API_KEY` the API starts but `/ask` returns 502.

## 4. Start

```
docker compose up --build -d
```

First build takes 2–4 minutes (uv and yarn layers are cached afterwards). Then poll `curl -fsS http://localhost:8000/health` (or the `APP_PORT` from `.env`) every 5 seconds for up to 3 minutes. Expected: `{"status":"ok"}`.

Then `docker compose ps`: `db`, `app`, `ui` running, `migrate` exited with code 0.

## 5. Verify

- API docs: http://localhost:8000/docs opens.
- UI: http://localhost:5173 shows API status «онлайн».
- `docker compose logs --tail 30 app` has no tracebacks.
- Optional, for IDE and lint: `cd app && uv sync`, `cd ui && yarn install --frozen-lockfile`. Show `uv run ruff check .` and `yarn lint` output.
- With the API running: `cd ui && yarn api:types` must finish without changing `src/api-types.ts` (`git status` clean). A diff means the backend and the committed types drifted; commit the regenerated file.

## 6. Railway (deploys)

Point to DEPLOYMENT.md, sections «Требования» and «Привязка CLI». Minimum to do now:
1. `railway login` (opens browser).
2. Ask the captain to add the user's email to the Railway project.
3. `cd app && railway link`, choosing the personal environment, never `production`.
4. Claude Code: run `/mcp`, approve the `railway` server from `.mcp.json`. Codex: trust the project so `.codex/config.toml` is read.

## 7. Report

Final message: a table of what is ready and what is left (keys, Railway link), URLs, and the two commands to remember: `docker compose up -d` to start, `docker compose down` to stop (`down -v` also drops the database).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `env_file` / `required` unknown key | Compose is older than 2.24, update Docker Desktop |
| `migrate` exits non-zero | `docker compose logs migrate`; usually the DB is not ready yet, rerun `docker compose up -d` |
| UI does not reload on edit (Windows) | expected to work via `VITE_USE_POLLING=true` in compose; check the volume mount of `ui/src` |
| Port already allocated | set `APP_PORT`/`UI_PORT`/`DB_PORT` in `.env` |
| CRLF warnings from git | ignore, `.gitattributes` normalizes to LF |
| Dev without Docker: settings not read | `config.py` reads `.env` from the current directory, so for `cd app && uv run python -m src` copy `.env` to `app/.env` (gitignored) and set `DATABASE_URL` host to `localhost` |

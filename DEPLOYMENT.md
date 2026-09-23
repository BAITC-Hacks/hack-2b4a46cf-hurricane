# Деплой

Всё живёт на Railway: бэкенд `app/`, бот, фронтенд `ui/` и Postgres в одном проекте `hurricane`. Цель: разработал фичу → через 1–2 минуты она доступна по публичному URL, без ngrok.

Схема:

| Окружение Railway | Кто деплоит | Как | Для чего |
|---|---|---|---|
| `production`, единственное | каждый со своей машины | `railway up` из `app/` или скилл `/deploy` | общая правда, ссылка в README, её показываем внешним |

**Автодеплоя из GitHub нет.** Репозиторий Организатора создан автоматически, Railway GitHub App в эту организацию не ставится. Поэтому сервисы в Railway пустые, а деплой всегда ручной с ноутбука. Следствие: в `production` попадает то, что лежит в рабочей папке деплоящего, а не то, что смержено в `main`. Проверять локально до `railway up`, а не после.

Фронт: сервис `ui` в том же проекте Railway, собирается из `ui/Dockerfile` (последний stage `prod`, nginx). Для локальной разработки фронта `yarn dev` направляется на бэкенд через `VITE_API_URL` в `ui/.env`.

## Требования

Обязательно у каждого в команде до старта:

1. **Railway CLI** установлен и залогинен.
   - macOS: `brew install railway`
   - Windows: `npm i -g @railway/cli` (или `scoop install railway`)
   - Проверка: `railway whoami`
2. **Railway MCP** подключён в project scope. Конфиги уже в репо, ничего ставить не надо, MCP отдаёт сам CLI:
   - Claude Code: `.mcp.json` в корне. При первом запуске в проекте Claude спросит разрешение на сервер `railway`, ответить «да». Проверка: `/mcp`.
   - Codex CLI: `.codex/config.toml` в корне. Codex читает project‑конфиг только в доверенном проекте: при первом запуске в папке ответить «trust», либо добавить в `~/.codex/config.toml` блок `[projects."<абсолютный путь к репо>"]` с `trust_level = "trusted"`. Проверка: `codex mcp list` (если команда есть в твоей версии) или спросить агента «какие MCP доступны».
   - Если project‑конфиг у Codex не подхватился, скопировать блок `[mcp_servers.railway]` из `.codex/config.toml` в `~/.codex/config.toml`.
   - `railway mcp` без аргументов проксирует удалённый сервер `mcp.railway.com`, это официальный дефолт и то, что ставит `railway setup agent`. Если сеть на площадке плохая, в обоих конфигах заменить `args` на `["mcp", "local"]`: сервер поднимется внутри CLI и будет ходить только в Railway API.
   - Опционально: `railway skills --agent claude-code` ставит user‑скилл `use-railway` от Railway с общими рецептами по платформе. Наш `/deploy` от него не зависит.
3. **Docker или Podman** для локальной проверки образа перед деплоем (не обязательно, но экономит неудачные билды).
4. Доступ в проект Railway команды: капитан приглашает по email в Project → Settings → Members.

## Первичная настройка проекта (капитан, один раз)

1. Railway → New Project → Empty project. Имя проекта = имя команды.
2. Добавить **Postgres** (Add → Database → PostgreSQL).
3. Добавить сервис **app**:
   - Source: Add → **Empty Service**, деплой в него через `railway up` из `app/`. GitHub‑источник не используется, см. выше.
   - Билдер и healthcheck подхватываются из `app/railway.json` (Dockerfile, `preDeployCommand` с миграциями, `healthcheckPath: /health`).
   - Variables: `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`, затем в значении заменить `postgresql://` на `postgresql+asyncpg://` (Railway отдаёт psycopg‑формат, SQLAlchemy async нужен asyncpg). Остальные из таблицы README «Переменные окружения»: `OPENAI_API_KEY`, `OPENAI_MODEL`, `CORS_ORIGINS`.
   - Settings → Networking → Generate Domain. Этот URL идёт в README и в `VITE_API_URL` фронта.
   - Если репо подключено: Settings → **Watch Paths** = `app/**`, иначе правки фронта пересобирают бэкенд.
4. Добавить сервис **ui**: Add → Empty Service, деплой через `railway up` из `ui/`. Билдер и healthcheck из `ui/railway.json`. Variables: `VITE_API_URL` = домен сервиса `app`. Переменная вшивается в бандл при сборке (в Dockerfile объявлена как `ARG`), после её изменения нужен redeploy. Порт nginx берётся из `PORT`, Railway задаёт его сам. Settings → Networking → Generate Domain, если репо подключено: **Watch Paths** = `ui/**`.
5. В `CORS_ORIGINS` сервиса `app` вписать домен сервиса `ui` и `http://localhost:5173`.

## Привязка CLI (каждый, один раз)

```
cd app
railway link
```

В диалоге выбрать workspace, проект `hurricane`, окружение `production`, сервис `app`. Проверка: `railway status` показывает `hurricane` и `production`.

Окружение одно на всех, отдельных доменов на разработчика нет: домен сервиса `app` общий, он же в README. Значит, деплои команды перетирают друг друга — договариваться голосом, кто сейчас катит.

Если когда-нибудь понадобится второе окружение: Environments → New Environment → **Duplicate** `production` (или `railway environment new <имя> --duplicate production`, проверено на CLI 5.58), затем `railway link --environment <имя>`.

## Ежедневный цикл

Из `app/`:

```
railway up --detach      # залить текущую папку, не ждать логов
railway logs             # поток логов рантайма
railway logs --deployment --lines 200   # последние строки, без потока
railway logs --build     # логи сборки, если билд упал
railway domain           # напомнить свой URL
railway open             # открыть сервис в дашборде
```

Или в Claude Code: `/deploy`. Скилл сам проверит логин, окружение, прогонит ruff, задеплоит и подождёт `/health`.

Или словами агенту через MCP: «задеплой app и покажи логи, если упадёт».

`railway up` загружает папку целиком, кроме файлов из `.gitignore`. `.venv`, `__pycache__` и `.env` туда не попадают. Если появится что-то тяжёлое вне gitignore, добавить `app/.railwayignore`.

Локальный фронт против задеплоенного бэкенда: в `ui/.env` поставить `VITE_API_URL=https://<домен app>.up.railway.app`, запустить `yarn dev`.

## Production

`production` — единственное окружение, и деплоит в него каждый сам из своей рабочей папки. Автодеплоя из `main` нет, поэтому дисциплина держится только на договорённостях:

- Перед `railway up` фича проверена локально: `docker compose up`, основной сценарий по README, `uv run ruff check .` зелёный.
- Деплоить из рабочей папки без незакоммиченного мусора: `railway up` заливает то, что лежит на диске, а не то, что в git.
- После деплоя проверить `https://<домен>/health` и основной сценарий.
- Ломающие изменения (миграция с удалением колонки, смена переменных) — не в одиночку, предупредить команду.
- MCP и CLI имеют права аккаунта на весь проект, включая удаление. Ничего не удалять, переменные не трогать без капитана.

## Почему деплой быстрый и как его не замедлить

- `app/Dockerfile` multi‑stage: слой с зависимостями кэшируется, при правке кода пересобирается только `COPY . .`. Не переставлять строки `COPY pyproject.toml uv.lock` и `COPY . .`.
- Новая зависимость = инвалидация кэша = плюс 1–2 минуты на билд. Добавлять пачкой, а не по одной.
- `healthcheckPath` в `railway.json`: трафик переключается на новую версию только после успешного `/health`. Ты не видишь 502 во время деплоя. Не убирать.
- `preDeployCommand` гоняет миграции до старта нового контейнера. Сломанная миграция = деплой не переключится, старая версия продолжит работать. Смотреть `railway logs --build`.

## Если что-то пошло не так

| Симптом | Причина | Что делать |
|---|---|---|
| `railway up` ругается на отсутствие link | не сделан `railway link` в `app/` | `railway link`, выбрать `hurricane` / `production` |
| Билд падает на `uv sync` | `uv.lock` не совпадает с `pyproject.toml` | `uv lock` локально, закоммитить, повторить |
| Контейнер стартует и падает | нет переменной или `DATABASE_URL` без `+asyncpg` | `railway variables`, сравнить имена с README |
| `/health` отдаёт 500 | БД недоступна, миграции не прошли | `railway logs --build`, проверить `preDeployCommand` |
| Фронт видит CORS‑ошибку | домена нет в `CORS_ORIGINS` | добавить origin, передеплоить |
| Фронт ходит не на тот API | `VITE_API_URL` вшит при сборке, переменную поменяли без пересборки | Redeploy сервиса `ui` |
| Сервис `ui` не проходит healthcheck | образ собрался не из stage `prod` или nginx слушает не `PORT` | `prod` должен оставаться последним stage в `ui/Dockerfile`, `PORT` не переопределять |
| `railway up` тащит сотни мегабайт | что-то большое вне `.gitignore` | `app/.railwayignore` |

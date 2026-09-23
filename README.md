# <Название проекта>

<2–3 предложения: что это и какую задачу решает.>

Демо: <ссылка на фронтенд Railway> · API: <ссылка на бэкенд Railway>/health

## Требования → статус

| Требование | Статус | Где в коде |
|---|---|---|
| <требование 1> | ✅ / ⚠️ частично / ❌ | `app/src/...` |

## Что реализовано

- Запрос к LLM через OpenAI API: `app/src/llm.py`, `POST /ask`
- Мультиязычный интерфейс ru / kk / en, адаптивная вёрстка: `ui/src`
- Главная страница `ui/src/routes/index.tsx`: фильтры подрядчика в стиле `DESIGN.md` (город, дата, формат, категория, бюджет; опционально язык и длительность). Кнопка показывает выбранные параметры, «Сбросить фильтры» возвращает исходные значения и очищает сводку; карточки не выдумываются.

## Архитектура

```
ui (React + Vite, Railway) ──HTTP/JSON──▶  app (FastAPI, Railway)  ──▶  Postgres (Railway)
                                              │
                                              └──▶ OpenAI API
```

- `app/src/main.py` роутеры, CORS, `/health`
- `app/src/models.py` таблицы, `app/migrations/` миграции, применяются контейнером `migrate` при старте
- `ui/src/api.ts` все запросы к бэкенду, типы из `ui/src/api-types.ts` (сгенерированы из OpenAPI), `ui/src/pages/` экраны

## Технологии и данные

- Бэкенд: Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, asyncpg, `openai`, uv
- Фронтенд: React 19, TypeScript, Vite 7, Tailwind CSS v4, shadcn на Base UI, Lingui, yarn, `openapi-fetch` с типами из `/openapi.json`
- База: PostgreSQL 17
- Инфраструктура: Railway, конфигурация в `.railway/railway.ts` (SDK `railway` в корневом `package.json`)
- Модель: `OPENAI_MODEL` (по умолчанию `gpt-5.4-mini`)
- Данные: каталог организатора, 66 профилей подрядчиков, `app/data/vendors.csv`. Загружается в таблицу `vendors` командой `python -m src.seed` (upsert по `id`, повторный запуск безопасен). В compose это делает сервис `seed` после миграций, на Railway `preDeployCommand`.

## Запуск

Нужны Docker Desktop или Podman Desktop с Compose и Python 3.9+. Ничего больше ставить не надо.

```bash
python dev.py
```

Скрипт проверит инструменты, создаст `.env` из `.env.example`, включит git-хуки, подберёт свободные порты, если стандартные заняты, соберёт и поднимет контейнеры и дождётся `/health`. В конце напечатает адреса: UI http://localhost:5173, API http://localhost:8000/docs. В Claude Code или Codex можно сказать `/setup`, агент запустит его сам и проверит результат.

После первого запуска вписать в `.env` `OPENAI_API_KEY` и повторить `python dev.py`. Остальные переменные имеют рабочие значения по умолчанию.

Другие команды: `python dev.py down` остановить (`down -v` также удалит базу), `python dev.py logs app` логи сервиса, `python dev.py status` состояние контейнеров, `python dev.py check` только проверка инструментов. Без скрипта то же самое делает `docker compose up --build`.

Compose поднимает Postgres, применяет миграции (сервис `migrate`), загружает каталог (сервис `seed`), затем стартует API и фронтенд.

### Разработка без Docker

```bash
# бэкенд (нужен запущенный Postgres, например `docker compose up db`)
cd app && uv sync && uv run alembic upgrade head && uv run python -m src.seed && uv run python -m src

# фронтенд
cd ui && yarn install && yarn dev
```

Типы API для фронтенда генерируются из спецификации бэкенда: при запущенном API выполнить `yarn api:types` в `ui/`, результат `ui/src/api-types.ts` коммитится. После изменения схем на бэкенде перегенерировать.

Проверки перед коммитом: `uv run ruff check . && uv run ruff format --check .` в `app/`, `yarn lint` в `ui/`.
Хук на сообщения коммитов: `git config core.hooksPath .githooks`.

## Как проверить основной сценарий

1. Открыть http://localhost:5173: на десктопе фильтры стоят в три колонки, на телефоне — в одну. Экран использует нейтральную палитру и отступы из `DESIGN.md`.
2. Выбрать город, дату, формат, категорию и бюджет. Язык и длительность находятся в блоке «Дополнительные условия».
3. Нажать «Применить»: ниже появится сводка введённых параметров и честное сообщение, что выдача подрядчиков пока не подключена.
4. Нажать «Сбросить фильтры»: форма вернётся к исходным значениям, сводка исчезнет.

## Переменные окружения

| Имя | Назначение | Пример |
|---|---|---|
| `OPENAI_API_KEY` | ключ OpenAI | `sk-...` |
| `OPENAI_MODEL` | модель | `gpt-5.4-mini` |
| `NVIDIA_API_KEY` | ключ NVIDIA API (генерация изображений, запасной LLM), необязательный | `nvapi-...` |
| `CORS_ORIGINS` | разрешённые origin через запятую | `https://<ui>.up.railway.app` |
| `DATABASE_URL` | строка подключения к Postgres | `postgresql+asyncpg://app:app@db:5432/app` |
| `VITE_API_URL` | адрес API для фронтенда | `https://<app>.up.railway.app` |

## Деплой

Подробно: [DEPLOYMENT.md](DEPLOYMENT.md) (`railway link`, `railway up`, MCP).

Всё на Railway, один проект `hurricane`, одно окружение `production`, три сервиса. Автодеплоя из GitHub нет, деплой ручной.

- **Postgres:** плагин Railway. Его `DATABASE_URL` подставить в сервис `app`, заменив префикс `postgresql://` на `postgresql+asyncpg://`.
- **app:** пустой сервис, деплой через `railway up` из `app/`, билдер Dockerfile. Переменные: `DATABASE_URL`, `OPENAI_API_KEY` и `CORS_ORIGINS` с публичным доменом сервиса `ui`. Миграции и загрузку каталога выполняет `preDeployCommand`. Настройки всех сервисов и регион `europe-west4` описаны в `.railway/railway.ts`.
- **ui:** пустой сервис, деплой через `railway up` из `ui/`, билдер Dockerfile (собирается последний stage `prod`). Переменная `VITE_API_URL` с публичным доменом сервиса `app` вшивается при сборке, после её изменения нужен redeploy. Порт берётся из `PORT`, который Railway задаёт сам.

## Известные ограничения

- Фильтры и диапазон дат на фронтенде временные (пометка `STUB:` в `SearchForm.tsx`); поиск по каталогу и карточки не подключены. Бэкенд не менялся.
- Для новых строк страницы пока нет переводов на казахский и английский.

## Команда

- <Имя, роль>


cd app && echo "$OPENAI_API_KEY" | railway variable set OPENAI_API_KEY --stdin --skip-deploys
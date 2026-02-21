# Рекомендации по пресетам

## VPS — рекомендации по типу проекта

| Тип проекта | Мин. CPU | Мин. RAM | Мин. диск |
|-------------|----------|----------|-----------|
| Статический сайт | 1 ядро | 1 ГБ | 15 ГБ |
| Backend (Node/Python/Go/PHP) | 1 ядро | 1-2 ГБ | 15-20 ГБ |
| Fullstack + БД | 2 ядра | 2-4 ГБ | 30-40 ГБ |
| Fullstack + БД + Redis | 2 ядра | 4 ГБ | 40 ГБ |

## App Platform — поддерживаемые фреймворки (нативно)

- **Node.js:** Express, Fastify, Hapi, Nest, Koa
- **Python:** Django, FastAPI, Flask, Celery
- **PHP:** Laravel, Symfony, Yii
- **Go:** Beego, Gin
- **Java:** Spring
- **.NET:** ASP.NET
- **Elixir:** Phoenix
- **Frontend:** React, Vue, Angular, Svelte, Next.js, Nuxt.js, Gatsby, Hugo и др.
- **Dockerfile / Docker Compose:** для всего остального

## App Platform — фреймворки через Dockerfile

Следующие фреймворки/рантаймы **не** поддерживаются нативно, но деплоятся через Dockerfile:

- **SvelteKit** — fullstack-фреймворк, деплоить как backend с Dockerfile
- **Remix** — fullstack-фреймворк, деплоить как backend с Dockerfile
- **Astro** — деплоить как frontend (static) или backend (SSR) с Dockerfile
- **Bun** — рантайм, деплоить через Dockerfile (заменить `node` на `oven/bun` в образе)
- **Deno** — рантайм, деплоить через Dockerfile (образ `denoland/deno`)
- **Fiber / Echo (Go)** — деплоить через Go Dockerfile
- **aiohttp / Tornado (Python)** — деплоить через Python Dockerfile

## App Platform — когда нужен Dockerfile

Если фреймворк/рантайм проекта **не** в нативном списке выше — нужен Dockerfile.
App Platform поддерживает деплой из Dockerfile и Docker Compose.

**ВАЖНО:** В Dockerfile обязателен `EXPOSE <порт>`, иначе App Platform не определит порт.

## App Platform — fullstack-проекты

App Platform не имеет типа `fullstack`. Fullstack-приложения (Next.js, Nuxt.js, SvelteKit, Remix) деплоятся как тип `backend` — они содержат и серверную часть, и фронтенд.

## Формат DATABASE_URL по типу БД

| БД | Формат |
|----|--------|
| PostgreSQL | `postgresql://user:pass@host:port/dbname` |
| MySQL | `mysql://user:pass@host:port/dbname` |
| MongoDB | `mongodb://user:pass@host:port/dbname` |
| Redis | `redis://:pass@host:port` |
| SQLite | `file:./data/app.db` (только VPS, не подходит для App Platform) |

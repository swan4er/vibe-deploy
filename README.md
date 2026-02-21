# vibe-deploy

Скилл для Claude Code и других агентов — автоматический деплой проектов на [Timeweb Cloud](https://timeweb.cloud).

## Что умеет

Разворачивает любой проект на Timeweb Cloud от анализа кода до рабочего URL:

- **Анализирует проект** — определяет рантайм, фреймворк, порт, БД, переменные окружения
- **Два пути деплоя** — App Platform (PaaS) или облачный сервер (VPS)
- **Рантаймы** — Node.js, Python, Go, PHP, статика (React/Vue/Svelte/Angular)
- **Docker** — создаёт Dockerfile и docker-compose из шаблонов, если нет своего
- **Базы данных** — PostgreSQL, MySQL, MongoDB, Redis через управляемый сервис
- **Домен, DNS, SSL** — привязка домена, настройка записей, Let's Encrypt
- **CI/CD** — GitHub Actions для автодеплоя при push в main
- **Возобновление** — сохраняет прогресс в `deploy-state.md`, можно продолжить с нужного шага

## Установка
Находясь в директории проекта, ведите команду ```npx skills add swan4er/vibe-deploy``` и следуйте инструкциям

## Как активировать
Введите команду ```/vibe-deploy```
Также скилл срабатывает, когда пользователь упоминает:

> задеплоить, развернуть, опубликовать, timeweb, twc, деплой

## Структура

```
vibe-deploy/
├── SKILL.md                        # Инструкции для ИИ-агента
├── scripts/
│   ├── analyze_project.py          # Анализ проекта (рантайм, фреймворк, порт, БД, env)
│   ├── timeweb_api.py              # Обёртка над Timeweb Cloud API
│   ├── github_api.py               # GitHub API (репо, secrets, deploy keys)
│   └── deploy_state.py             # Управление файлом состояния деплоя
├── templates/
│   ├── dockerfiles/                # Dockerfile для Node, Python, Go, PHP, React, fullstack
│   ├── nginx/                      # Конфиги nginx (reverse proxy, static site)
│   ├── systemd/                    # Unit-файлы для Node (PM2), Python (gunicorn), Go
│   └── workflows/                  # GitHub Actions для VPS и App Platform
└── reference/
    ├── api-endpoints.md            # Справочник эндпоинтов Timeweb Cloud API
    ├── errors.md                   # Таблица ошибок и инструкции по откату
    └── presets-guide.md            # Пресеты серверов, БД, App Platform
```

## Зависимости

- **Python 3** — для скриптов (агент проверит наличие перед началом)
- **PyNaCl** — только если нужна автоматическая настройка GitHub Secrets: `pip install pynacl`
- **API-токен Timeweb Cloud** — агент запросит и сохранит в `~/.config/timeweb/.env`

## Процесс деплоя

```
1. Анализ проекта + создание deploy-state.md
2. Получение API-токена Timeweb Cloud
3. Проверка баланса аккаунта
4. Выбор стратегии: App Platform или VPS
5. Подготовка: Docker, env-переменные, конфиги
6. Создание инфраструктуры (сервер/приложение, БД)
7. Деплой проекта
8. Настройка домена, DNS, SSL
9. Настройка CI/CD (GitHub Actions)
10. Финальная проверка + сводка для пользователя
```

## Безопасность

- Репозитории создаются только **приватными**
- `deploy-state.md` и `DEPLOY.md` добавляются в `.gitignore`
- SSH-ключи хранятся в `~/.ssh/`, токены в `~/.config/timeweb/`
- Приложение на VPS запускается от непривилегированного пользователя `app`
- Firewall (ufw) и fail2ban настраиваются автоматически

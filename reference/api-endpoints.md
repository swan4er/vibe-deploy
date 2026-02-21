# Timeweb Cloud API — Справочник эндпоинтов

Базовый URL: `https://api.timeweb.cloud`

Заголовки для всех запросов:
```
Authorization: Bearer $TIMEWEB_CLOUD_TOKEN
Content-Type: application/json
```

## Аккаунт
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /api/v1/account/status | Статус аккаунта |
| GET | /api/v1/account/finances | Баланс |

## Серверы (VPS)
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /api/v1/presets/servers | Пресеты (тарифы) |
| GET | /api/v1/os/servers | Образы ОС |
| GET | /api/v1/servers | Список серверов |
| POST | /api/v1/servers | Создать сервер |
| GET | /api/v1/servers/{id} | Информация о сервере |
| DELETE | /api/v1/servers/{id} | Удалить сервер |
| POST | /api/v1/servers/{id}/ips | Добавить IP-адрес |

## SSH-ключи
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /api/v1/ssh-keys | Список ключей |
| POST | /api/v1/ssh-keys | Загрузить ключ |

## App Platform
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /api/v1/apps/frameworks | Доступные фреймворки |
| GET | /api/v1/apps/presets | Пресеты (тарифы) |
| GET | /api/v1/apps | Список приложений |
| POST | /api/v1/apps | Создать приложение |
| GET | /api/v1/apps/{id} | Статус приложения |
| DELETE | /api/v1/apps/{id} | Удалить приложение |
| POST | /api/v1/apps/{id}/deploy | Запустить деплой |
| GET | /api/v1/apps/{id}/logs | Логи приложения |

## Базы данных
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /api/v1/presets/dbs | Пресеты БД |
| GET | /api/v1/dbs | Список БД |
| POST | /api/v1/dbs | Создать БД |
| GET | /api/v1/dbs/{id} | Информация о БД |
| DELETE | /api/v1/dbs/{id} | Удалить БД |

## Домены и DNS
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /api/v1/domains | Список доменов |
| POST | /api/v1/domains | Добавить домен |
| GET | /api/v1/domains/available?fqdn=X | Проверить доступность |
| POST | /api/v1/domains/orders | Заказать домен |
| GET | /api/v1/domains/{fqdn}/dns-records | DNS-записи |
| POST | /api/v1/domains/{fqdn}/dns-records | Добавить DNS-запись |

## S3 / Firewall
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET/POST | /api/v1/storages/buckets | S3-бакеты |
| GET/POST | /api/v1/firewall/groups | Firewall-группы |

## Документация
Если эндпоинт возвращает ошибку — проверь актуальную документацию:
```bash
curl -s "https://timeweb.cloud/api-docs-data/bundle.json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for path, methods in data.get('paths', {}).items():
    if 'KEYWORD' in path.lower():
        for method, info in methods.items():
            print(f'{method.upper()} {path} — {info.get(\"summary\", \"\")}')"
```

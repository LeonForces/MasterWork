# Платформа видеоаналитики реального времени

Репозиторий содержит E2E MVP платформы видеоаналитики для магистерской ВКР. Система принимает видеопоток или демо-видео, выполняет обнаружение объектов, ведет треки, применяет правила событийного анализа и доставляет события через API, RabbitMQ и webhook-интеграцию.

Основной демонстрационный сценарий - обнаружение БПЛА на подготовленном видео `videos/V_DRONE_009.mp4` с использованием обученной модели `runs/detect/runs/train/small_detection/weights/best.pt`.

## Что реализовано

- Управление пользователями, ролями и доступом через `JWT + RBAC`.
- CRUD для камер, зон контроля и правил событийного анализа.
- Обработка видео в `analytics-worker`: захват кадров, inference, tracking, rule engine.
- Хранение событий и outbox-записей в `PostgreSQL`.
- Публикация событий в `RabbitMQ` и доставка во внешний webhook с retry/DLQ.
- Веб-интерфейс оператора на `React`: dashboard, demo, cameras, zones, rules, events, status.
- Наблюдаемость через `/metrics`, `Prometheus` и `Grafana`.
- Контракты API и событий в каталоге `contracts`.
- Автоматизированные smoke- и acceptance-проверки для функциональности, RBAC и надежности доставки.

## Состав проекта

| Путь | Назначение |
|---|---|
| `services/api` | FastAPI control plane: авторизация, конфигурация, события, health/metrics |
| `services/analytics-worker` | Data plane: обработка видео, детекция, трекинг, генерация событий |
| `services/integration-worker` | Публикация outbox-событий в RabbitMQ и доставка webhook-уведомлений |
| `services/ui` | React SPA для оператора и проверяющего |
| `services/webhook-mock` | Тестовый consumer для проверки доставки событий |
| `contracts` | `event.schema.v1.json` и snapshot OpenAPI-контракта |
| `infra/prometheus`, `infra/grafana` | Конфигурация мониторинга |
| `scripts` | Smoke, acceptance и вспомогательные сценарии |
| `docs/MasterWork` | Архитектура, отчет, презентация и финальный пакет сдачи |

## Требования

Для локального запуска нужны:

- Docker и Docker Compose (`docker compose` или `docker-compose`);
- `make`;
- Python 3 для локальных smoke/acceptance-скриптов;
- Node.js/npm для локальной установки и проверки UI через `make bootstrap` и `make verify`.

Перед первым запуском убедитесь, что стандартные порты свободны. Если заняты `8000` или `4173`, используйте изолированный E2E-профиль из раздела ниже.

## Быстрый старт

1. Подготовить `.env` и локальные зависимости UI:

```bash
make bootstrap
```

Если `.env` уже существовал раньше, проверьте, что `JWT_SECRET_KEY` содержит не менее 32 символов.

2. Запустить стек в фоне:

```bash
make up-d
```

3. Применить миграции:

```bash
make migrate-up
```

4. Открыть интерфейсы:

- UI: `http://localhost:4173`
- API docs: `http://localhost:8000/docs`
- RabbitMQ Management: `http://localhost:15672`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Webhook mock: `http://localhost:8090`

5. Войти в UI:

- username: `admin`
- password: `admin12345`

Значения задаются в `.env` через `DEFAULT_ADMIN_USERNAME` и `DEFAULT_ADMIN_PASSWORD`.

## Демо обнаружения БПЛА

Стек по умолчанию настроен на демо-сценарий:

- модель: `runs/detect/runs/train/small_detection/weights/best.pt`
- видео: `videos/V_DRONE_009.mp4`
- путь модели внутри контейнера: `/app/models/best.pt`
- путь видео внутри контейнера: `/app/videos/V_DRONE_009.mp4`

После запуска откройте `http://localhost:4173/demo`. При `DEMO_DRONE_ENABLED=true` API автоматически создает активную demo camera, а `analytics-worker` пишет текущие треки в `/api/v1/tracks` и события правил в `/api/v1/events`.

При `DEMO_DRONE_EXCLUSIVE=true` старые non-demo cameras переводятся в inactive, чтобы worker сфокусировался на загруженном видео.

## Основные страницы UI

- `http://localhost:4173/dashboard` - обзор состояния платформы.
- `http://localhost:4173/demo` - демонстрация обнаружения БПЛА и текущих треков.
- `http://localhost:4173/events` - журнал событий, acknowledgement и evidence export.
- `http://localhost:4173/cameras` - камеры и источники видео.
- `http://localhost:4173/zones` - зоны контроля.
- `http://localhost:4173/rules` - правила событийного анализа.
- `http://localhost:4173/status` - health/status сервисов.

## Проверка результата

Базовая проверка кода и сборки:

```bash
make verify
```

Smoke-сценарий против запущенного основного стека:

```bash
make smoke-e2e
```

Полный acceptance-сценарий против основного стека:

```bash
make acceptance-e2e
```

`acceptance-e2e` проверяет функциональный E2E-поток, ограничения `RBAC`, устойчивость outbox при остановке RabbitMQ и retry-доставку при временной недоступности webhook.

## Изолированный E2E-профиль

Если стандартные host-порты заняты другим проектом, используйте отдельный compose-проект:

```bash
make e2e-up-d
make e2e-migrate-up
make e2e-smoke
make e2e-acceptance-artifact
```

В этом профиле доступны:

- UI: `http://localhost:14173`
- API docs: `http://localhost:18000/docs`
- RabbitMQ Management: `http://localhost:15673`
- Prometheus: `http://localhost:19090`
- Grafana: `http://localhost:13000`
- Webhook mock: `http://localhost:18090`

Acceptance-артефакт сохраняется в `docs/MasterWork/REPORT/LaTeX/acceptance_results_2026-05-13.json`.

## Полезные команды

```bash
make ps
make logs SERVICES="api integration-worker"
make logs-api
make logs-analytics
make logs-integration
make migrate-up
make down
```

Полная остановка с удалением volume-данных:

```bash
make down-v
```

Сборка PDF-отчета ВКР через dockerized TeX Live:

```bash
make report-pdf
make report-check
```

## Конфигурация

Основные параметры находятся в `.env`, который создается из `.env.example`.

Ключевые значения по умолчанию:

- `UI_API_BASE_URL=http://localhost:8000`
- `POSTGRES_HOST_PORT=55432`
- `RABBITMQ_EXCHANGE=events.topic.v1`
- `WEBHOOK_TARGET_URL=http://webhook-mock:8090/webhook/events`
- `DETECTOR_MODEL=/app/models/best.pt`
- `DETECTOR_CLASSES=drone,bird`
- `USE_MOCK_DETECTOR=false`
- `DEMO_DRONE_ENABLED=true`
- `DEMO_DRONE_SOURCE=/app/videos/V_DRONE_009.mp4`

RabbitMQ Management использует значения `RABBITMQ_USER` и `RABBITMQ_PASSWORD` из `.env`. Grafana по умолчанию доступна с `admin` / `admin`.

## Документация и материалы ВКР

- Архитектура: `docs/MasterWork/ARCHITECTURE.md`.
- Финальный пакет сдачи: `docs/MasterWork/FINAL_DELIVERY`.
- Основной PDF-отчет: `docs/MasterWork/FINAL_DELIVERY/main.pdf`.
- Презентация: `docs/MasterWork/FINAL_DELIVERY/PRESENTATION.pptx`.
- Речь к защите: `docs/MasterWork/FINAL_DELIVERY/SPEECH.md`.
- Манифест проверок: `docs/MasterWork/FINAL_DELIVERY/MANIFEST.md`.

## Примечания

- Базовая конфигурация CPU-first. Аппаратное ускорение является направлением дальнейшей оптимизации и не требуется для текущего принятого результата.
- Контракт события версии 1 находится в `contracts/event.schema.v1.json`.
- Формат routing key: `event.<event_type>.v1`.

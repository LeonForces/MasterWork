# Финальный пакет сдачи

Дата подготовки: 2026-05-13.

## Состав

- `main.pdf` - основной сдаваемый отчет.
- `Otchet_magisterskaya_diplomnaya_rabota.docx` - вторичный DOCX-экспорт.
- `PRESENTATION.pptx` - защитная презентация на 11 слайдов.
- `SPEECH.md` - речь к презентации на 7-10 минут.
- `acceptance_results_2026-05-13.json` - сохраненный acceptance-артефакт с результатом `passed`.
- `MANIFEST.md` - контрольный список и статус проверок.

## Команды запуска

```bash
make bootstrap
make up-d
make migrate-up
make smoke-e2e
make acceptance-e2e
```

Если стандартный порт `8000` занят другим проектом, используйте изолированный E2E-профиль:

```bash
make e2e-up-d
make e2e-migrate-up
make e2e-smoke
make e2e-acceptance-artifact
```

Изолированный UI в этом профиле доступен на `http://localhost:14173`, API - на `http://localhost:18000`.

UI после запуска стека:

- `http://localhost:4173/dashboard`
- `http://localhost:4173/demo`
- `http://localhost:4173/events`
- `http://localhost:4173/cameras`
- `http://localhost:4173/zones`
- `http://localhost:4173/rules`
- `http://localhost:4173/status`

## Проверки

В текущем окружении выполнены `make verify`, локальная сборка `main.pdf`, структурная проверка PPTX и DOCX, UI smoke через браузер с проверкой `Acknowledge` и `Export evidence` через реальные API mutation/download, а также изолированный `make e2e-smoke` и `make e2e-acceptance-artifact` на `localhost:18000`.

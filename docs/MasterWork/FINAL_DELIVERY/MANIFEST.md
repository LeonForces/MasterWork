# MANIFEST

Дата: 2026-05-13

## Реквизиты

- Кафедра: 806
- Исполнитель: Нурмухамедов А.Б.
- Руководитель: Гаврилов Константин Юрьевич, д.т.н., профессор
- Город: Москва
- Год: 2026

## Артефакты

- [x] `main.pdf`
- [x] `Otchet_magisterskaya_diplomnaya_rabota.docx`
- [x] `PRESENTATION.pptx`
- [x] `SPEECH.md`
- [x] `acceptance_results_2026-05-13.json`
- [x] `README.md`

## Проверки 2026-05-13

- [x] `make verify`: пройден.
- [x] API tests: 6 passed.
- [x] Analytics-worker tests: 3 passed, 1 skipped.
- [x] Integration-worker tests: 5 passed.
- [x] UI build: пройден.
- [x] UI smoke: `/dashboard`, `/demo`, `/events`, `/status`; `Acknowledge` и `Export evidence` проверены через реальные API mutation/download.
- [x] Isolated E2E smoke: `make e2e-smoke` на `http://localhost:18000`.
- [x] Isolated acceptance: `make e2e-acceptance-artifact`, результат `passed`, длительность `30.732` с.
- [x] Isolated UI smoke: login/dashboard/events через `http://localhost:14173` с API `http://localhost:18000`.
- [x] Report build: `main.pdf` пересобран локальным TeX Live 2026; undefined references/citations не найдены.
- [x] PPTX: 11 слайдов, package QA без failures.
- [x] DOCX: файл открывается через OOXML parser; титул содержит исполнителя, руководителя, кафедру, город и год.
- [x] Docker stack rerun: выполнен через изолированный профиль `docker-compose.e2e.yml` со смещенными host-портами.

## Примечания

Главным документом сдачи является PDF. DOCX включен как вторичный артефакт и прошел структурную проверку; визуальный render DOCX не выполнен, так как в окружении недоступен LibreOffice/`soffice`.

Количественно заявленные результаты основаны на CPU/E2E acceptance, БПЛА-демо, UI triage и надежной доставке событий. Аппаратное ускорение инференса оставлено как направление развития.

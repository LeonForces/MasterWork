# Как использовать LaTeX в этом проекте

Основной файл отчета: `docs/MasterWork/REPORT/LaTeX/main.tex`.

Сборка в проекте идет по цепочке:

```text
xelatex -> biber -> xelatex -> xelatex
```

Это важно, потому что в проекте используются:

- русский текст через `polyglossia`;
- системные шрифты через `fontspec`;
- библиография через `biblatex` + `biber`;
- стиль ссылок `gost-numeric` из `biblatex-gost`.

Поэтому обычный `pdflatex` для этого проекта не подходит. Нужен именно `xelatex`.

## Самый простой вариант

Если тебе нужен только PDF и не хочется ставить LaTeX локально, в репозитории уже есть готовая docker-сборка:

```bash
make report-pdf
```

Команду нужно запускать из корня репозитория.

Готовый PDF появится здесь:

```text
docs/MasterWork/REPORT/LaTeX/main.pdf
```

Этот вариант удобен, если хочешь просто собирать отчет и не настраивать TeX вручную.

## Локальная установка для работы в VS Code

Если хочешь собирать LaTeX прямо из VS Code с предпросмотром PDF, поставь полную TeX-дистрибуцию. Для этого проекта так надежнее, чем докачивать пакеты по одному.

### macOS

Для macOS проще всего поставить MacTeX:

- официальный сайт: https://www.tug.org/mactex/

После установки перезапусти терминал и VS Code, затем проверь:

```bash
which xelatex
which biber
which latexmk
```

Если `xelatex` не находится, обычно нужно добавить в `PATH`:

```bash
/Library/TeX/texbin
```

### Windows

Для Windows удобнее всего MiKTeX:

- официальный сайт: https://miktex.org/download

Что важно после установки:

- включить автоматическую установку недостающих пакетов;
- открыть `MiKTeX Console` и поставить обновления;
- перезапустить VS Code.

### Linux

На Linux проще всего поставить полный `TeX Live`.

Для Ubuntu/Debian обычно хватает:

```bash
sudo apt update
sudo apt install texlive-full biber latexmk
```

Если не хочешь ставить полный набор пакетов, будь готов отдельно разбирать ошибки по отсутствующим пакетам. Для этого проекта полный набор обычно экономит время.

## Какие библиотеки нужны проекту

Минимально тебе нужны:

- `xelatex`;
- `biber`;
- `latexmk`;
- пакеты из `preamble.tex`, в том числе `fontspec`, `polyglossia`, `biblatex`, `biblatex-gost`, `csquotes`, `geometry`, `setspace`, `booktabs`, `longtable`, `tabularx`, `multirow`, `enumitem`, `graphicx`, `caption`, `hyperref`, `fancyhdr`.

Отдельно руками ставить их обычно не нужно, если установлен:

- `MacTeX` на macOS;
- полный `TeX Live` на Linux;
- `MiKTeX` с автоустановкой missing packages на Windows.

## Установка расширения в VS Code

Для работы с LaTeX в VS Code поставь расширение:

- `LaTeX Workshop` by James Yu

Через интерфейс VS Code:

1. Открой `Extensions`.
2. Найди `LaTeX Workshop`.
3. Нажми `Install`.

Или через терминал:

```bash
code --install-extension James-Yu.latex-workshop
```

## Как собирать отчет в VS Code

1. Открой в VS Code весь репозиторий.
2. Открой файл `docs/MasterWork/REPORT/LaTeX/main.tex`.
3. Запусти команду `LaTeX Workshop: Build with recipe`.
4. Выбери рецепт:
   - `latexmk (xelatex)`, если он есть;
   - или `xelatex -> biber -> xelatex -> xelatex`.
5. Открой PDF через `LaTeX Workshop: View LaTeX PDF`.

Важно:

- собирать нужно именно `main.tex`;
- файлы вроде `introduction.tex`, `chapter1_problem_statement.tex` и другие главы отдельно не собираются;
- если редактируешь главу, результат все равно собирается через `main.tex`.

## Если VS Code собирает не тем движком

Если по умолчанию запускается `pdflatex`, появятся ошибки, связанные с `fontspec` или русским текстом. В этом случае выбери рецепт с `xelatex`.

При необходимости можно добавить настройки в `.vscode/settings.json`:

```json
{
  "latex-workshop.latex.autoBuild.run": "onSave",
  "latex-workshop.latex.recipe.default": "lastUsed",
  "latex-workshop.view.pdf.viewer": "tab"
}
```

После этого один раз вручную выбери рецепт `latexmk (xelatex)` или `xelatex -> biber -> xelatex -> xelatex`, и VS Code будет использовать его дальше.

## Проверка, что все работает

Из корня репозитория:

```bash
cd <repo-root>
make report-pdf
```

Если хочешь собирать локально без Docker, то проверь:

```bash
cd docs/MasterWork/REPORT/LaTeX
xelatex -interaction=nonstopmode -halt-on-error main.tex
biber main
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

## Частые проблемы

### Ошибка `fontspec requires either XeTeX or LuaTeX`

Причина: запущен `pdflatex`.

Решение: переключить рецепт сборки на `xelatex`.

### Ошибка `biber not found`

Причина: не установлен `biber`.

Решение:

- macOS: переустановить или обновить `MacTeX`;
- Linux: установить пакет `biber`;
- Windows: поставить `biber` через `MiKTeX Console` или разрешить автоустановку.

### Не собирается библиография

Причина: была выполнена только одна LaTeX-сборка без шага `biber`.

Решение: использовать полную цепочку:

```text
xelatex -> biber -> xelatex -> xelatex
```

### В VS Code открыт файл главы, а сборка не стартует

Причина: корневой файл проекта не выбран.

Решение: открыть и собирать `main.tex`.

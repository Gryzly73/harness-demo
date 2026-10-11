# Демонстрация Agentic Harness: minisearch, два режима

Небольшая поисковая библиотека на русском и английском языках используется как
целевой продукт для Agentic Harness:

```text
цель → план → loop
```

Готовность подтверждается объективными проверками вне AI-агента.

> Это русская справочная версия корневого `README.md`. Рабочие имена файлов,
> команд и параметров оставлены без перевода.

## Документация

- [спецификация](SPEC.md);
- [паспорт для агента](AGENTS.md);
- [журнал прогресса](PROGRESS.md);
- [поисковик для заказчика](../../ДЛЯ_ЗАКАЗЧИКА.md);
- [Harness для заказчика](../../HARNESS_ДЛЯ_ЗАКАЗЧИКА.md);
- [исходный проект и доработки](../../ИСХОДНЫЙ_ПРОЕКТ_И_ДОРАБОТКИ.md);
- [переводы Cursor-команд](cursor-commands/).

## Режимы

| Режим | Исходное состояние | Кто пишет план | Что демонстрирует |
|---|---|---|---|
| `brownfield` | работающий код, отсутствуют три функции | человек, готовый `PLAN.md` | loop, динамическое перепланирование, защита |
| `greenfield` | контракт в `SPEC.md`, пустой `src/` | агент через `/plan`, затем валидатор и человек | полный путь от цели до плана и реализации |

## Структура

```text
harness/plan.py, validate_plan.py   парсер и валидатор плана
harness/loop.py                     plan phase и общий loop
loop.ps1, loop.sh                   обёртки Windows и POSIX
.cursor/                            rules, commands и hooks
tests/acceptance/, eval/, data/     защищённый проверочный оракул
modes/<mode>/                       overlay выбранного режима
demo/                               offline-агент и reference solution
```

## Быстрый запуск

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
.\use_mode.ps1 greenfield
git add -A
git commit -m "greenfield baseline"
$env:AUTO_APPROVE = "1"
.\loop.ps1
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
./use_mode.sh greenfield
git add -A && git commit -m "greenfield baseline"
AUTO_APPROVE=1 ./loop.sh
```

Для настоящего контрольного запуска используйте отдельную копию:

```powershell
.\use_mode.ps1 greenfield --strip
```

или:

```bash
./use_mode.sh greenfield --strip
```

Флаг удаляет `modes/`, `demo/` и `DEMO.md`, чтобы агент физически не имел доступа
к reference solution. `.cursorignore` также скрывает эти материалы, но является
дополнительной, а не основной защитой.

## Переменные окружения

```text
MAX_ITER=12
MAX_FAILS=3
ITER_TIMEOUT=600
PLAN_TRIES=3
AUTO_APPROVE=0
AGENT_CMD=...
```

## Что гарантирует Harness

- у каждой задачи плана есть `done when`;
- план покрывает все acceptance-тесты;
- проверки красные до реализации;
- перед loop предусмотрено подтверждение плана человеком;
- каждая итерация использует свежую агентскую сессию;
- изменения защищённого оракула откатываются;
- из изменений плана разрешено только добавление подзадач;
- task-check и `make check` запускаются самим Harness;
- только Harness ставит галочки и создаёт коммиты в `loop/*`;
- действуют лимиты итераций, времени и повторных ошибок;
- `.loop/metrics.csv` сохраняет измеримые результаты.

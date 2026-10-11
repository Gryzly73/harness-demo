# Спецификация: minisearch (greenfield)

> Русский перевод `SPEC.md` для чтения. Машинным контрактом Harness остаётся
> корневой файл `SPEC.md`.

## Цель

Создать с нуля компактную библиотеку поиска по коротким русским и английским
текстам. В runtime разрешена только стандартная библиотека Python. Сеть и файлы
моделей не требуются. Версия Python — 3.10 или новее.

Качество должно измеряться командой:

```text
python -m minisearch.evaluate
```

## Контракт пакета `src/minisearch/`

`__init__.py` должен экспортировать `Document`, `HashingEmbedder`, `Index` и
`load_jsonl`.

| Модуль | Контракт |
|---|---|
| `corpus.py` | Неизменяемый dataclass `Document(id: str, text: str, lang: str = "en")`. Функция `load_jsonl(path) -> list[Document]` читает UTF-8 JSONL с полями `id`, `text`, `lang` и пропускает пустые строки. |
| `tokenize.py` | `tokenize(text: str) -> list[str]`: нижний регистр и разбиение на словесные токены. |
| `embed.py` | `HashingEmbedder(dim: int = 1024)` с `.dim` и `.embed(text) -> list[float]`: hashing trick для bag-of-words, единичная длина вектора, нулевой вектор для текста без токенов. |
| `index.py` | `Index(embedder)` с `.add(doc)`, `.add_many(docs)`, `.search(query, k=5) -> list[tuple[Document, float]]`: cosine similarity, лучшие результаты первыми, одинаковые оценки сортируются по id, возвращаются только оценки выше нуля. |
| `cli.py` | `python -m minisearch.cli search QUERY [--corpus F] [-k N] [--format text\|json\|csv] [--output PATH]`; корпус по умолчанию — `data/corpus.jsonl`. Текстовый формат по умолчанию: `<doc_id>\t<score:.3f>\t<первые 60 символов текста>`. |
| `evaluate.py` | Предоставлен и защищён. Импортирует `Index`, `HashingEmbedder`, `load_jsonl` и путь к корпусу. Изменять нельзя. |

## Функции в порядке реализации

1. **Ядро**: весь контракт выше. Английский `recall@3` не ниже `0.8` на
   `eval/en.jsonl`.
2. **Сохранение индекса**: `Index.save(path)`, `Index.load(path, embedder)`;
   CLI-команды `index --corpus F --out P` и `search Q --index P`. Индекс,
   построенный одним процессом, должен работать в другом.
3. **Русский язык**: `recall@3` не ниже `0.9` на `eval/ru.jsonl`; английский
   показатель не должен опуститься ниже `0.8`.
4. **Языковой фильтр**: `Index.search(query, k, lang=None)` и CLI `--lang`.
5. **Выгрузка результатов**: CLI `--format text|json|csv` и необязательный
   `--output PATH`. JSON содержит UTF-8 массив, CSV — строку заголовков. Поля:
   `id`, `score`, `text`, `lang`. Без `--output` результат выводится в stdout.
   Текстовый формат остаётся значением по умолчанию.

## Общая приёмка каждой итерации

Команда `make check` должна подтверждать:

```text
ruff check .
pytest -q
python -m minisearch.evaluate --set en --min-recall 0.8
```

## Проверочный оракул

Следующие материалы созданы человеком и недоступны для изменения агентом:

```text
tests/acceptance/
eval/
data/
SPEC.md
src/minisearch/evaluate.py
harness/
loop.sh
.cursor/
```

Каждый файл из `tests/acceptance/` должен быть указан в `done when` хотя бы одной
задачи плана.

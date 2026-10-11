# Результат демонстрационной выгрузки

Файлы в этом каталоге сформированы функциональной версией `minisearch` из ветки
`loop/1011-101629` на корпусе `examples/test-data/corpus.jsonl`.

Запрос:

```text
как подключить удалённый доступ через VPN
```

Параметры:

```text
lang=ru
k=5
```

Результаты:

- `search_ru.json` — UTF-8 JSON;
- `search_ru.csv` — CSV, совместимый с Excel.

Команда для JSON:

```powershell
$env:PYTHONHASHSEED = "0"  # воспроизводимый демонстрационный результат
python -m minisearch.cli search "как подключить удалённый доступ через VPN" `
  --corpus examples/test-data/corpus.jsonl `
  --lang ru `
  -k 5 `
  --format json `
  --output examples/test-output/search_ru.json
```

Для CSV замените `--format json` на `--format csv` и расширение файла на `.csv`.

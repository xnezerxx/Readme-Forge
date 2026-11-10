# readme-forge

![Language](https://img.shields.io/badge/language-Python-informational) ![License](https://img.shields.io/badge/license-MIT-blue)

Генератор README, который сам изучает проект. Определяет язык, зависимости из манифестов разных экосистем, лицензию и git-remote, строит структуру папок и добавляет бейджи. Экспортирует в Markdown и в самостоятельную HTML-страницу. Нужен только Python 3.9+ (для разбора `pyproject.toml` удобнее 3.11+). Внешних библиотек нет.

## Возможности

- Определение основного языка по маркерным файлам (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `Gemfile`, `composer.json`, `pom.xml` и др.)
- Зависимости из `requirements.txt`, `pyproject.toml` (PEP 621 и Poetry), `package.json`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`
- Распознавание лицензии: MIT, Apache-2.0, GPL-3.0, BSD-3-Clause, Unlicense
- Чтение `origin` из git для ссылки клонирования и бейджа звёзд
- Дерево проекта без служебных папок (`node_modules`, `.git`, `.venv` и др.)
- Мастер вопросов (`--interactive`) для описания и дополнительных разделов
- JSON-конфиг с дополнительными разделами
- Экспорт в `README.md`, `README.html` или оба формата сразу
- Защита от перезаписи существующих файлов без `--force`

## Установка

```bash
git clone https://github.com/xnezerxx/readme-forge.git
cd readme-forge
```

## Использование

Графическое окно (самый простой способ):

```bash
python -m readme_forge.gui
```

В окне выбираете папку проекта, пишете описание, при необходимости добавляете разделы, нажимаете «Создать предпросмотр» и «Сохранить файлы». Окно работает на Windows, macOS и Linux, которые поставляются с tkinter.

Сборка exe для Windows (делается на Windows, нужен Python):

```bat
build.bat
```

Готовый файл появится в папке `dist\readme-forge.exe`.

Командная строка.

Сгенерировать README для текущей папки:

```bash
python -m readme_forge . -d "Короткое описание" -u "python main.py"
```

Пошаговый мастер:

```bash
python -m readme_forge /путь/к/проекту --interactive
```

Оба формата сразу:

```bash
python -m readme_forge . --format both --force
```

Посмотреть результат без записи файлов:

```bash
python -m readme_forge . --print
```

Пример конфига (`examples/config.json`):

```json
{
  "description": "Инструмент для автоматической документации",
  "usage": "python main.py --help",
  "sections": {
    "Roadmap": "- Поддержка Go-проектов\n- Экспорт в PDF"
  }
}
```

Запуск с конфигом: `python -m readme_forge . -c examples/config.json`

## Тесты

```bash
python -m unittest discover -s tests -v
```

Набор включает 32 теста (один пропускается, если нет дисплея для окна): разбор манифестов, экспорт в HTML, мастер вопросов и сценарии командной строки.

## Структура

```text
readme-forge/
├── readme_forge/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── core.py
│   ├── exporters.py
│   ├── gui.py
│   ├── parsers.py
│   ├── service.py
│   └── wizard.py
├── tests/
│   ├── test_core.py
│   ├── test_extras.py
│   ├── test_gui.py
│   └── test_service.py
├── examples/
│   └── config.json
├── build.bat
├── run_gui.py
├── LICENSE
└── README.md
```

## Лицензия

Распространяется по лицензии MIT.

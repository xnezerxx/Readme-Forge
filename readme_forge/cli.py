"""Командная строка readme-forge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import render_readme, scan_project, write_readme
from .exporters import markdown_to_html
from .wizard import run_wizard

DEFAULT_USAGE = "python main.py"


def load_config(path: Path | None) -> dict:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Конфиг не найден: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="readme-forge",
        description="Автоматически создаёт README по содержимому проекта.",
    )
    parser.add_argument("path", nargs="?", default=".", type=Path,
                        help="путь к проекту (по умолчанию текущая папка)")
    parser.add_argument("-d", "--description", default=None,
                        help="описание проекта в одну-две строки")
    parser.add_argument("-u", "--usage", default=None,
                        help=f"команда запуска (по умолчанию: {DEFAULT_USAGE})")
    parser.add_argument("-c", "--config", type=Path,
                        help="JSON-файл с дополнительными разделами")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="задать описание и разделы через мастер вопросов")
    parser.add_argument("--format", choices=["md", "html", "both"], default="md",
                        help="формат результата: md, html или both")
    parser.add_argument("-f", "--force", action="store_true",
                        help="перезаписать существующие файлы")
    parser.add_argument("--print", action="store_true", dest="print_only",
                        help="вывести Markdown в консоль, не записывая файлы")
    parser.add_argument("-V", "--version", action="version",
                        version=f"%(prog)s {__version__}")
    return parser


def _target_files(root: Path, fmt: str) -> list[Path]:
    targets = []
    if fmt in ("md", "both"):
        targets.append(root / "README.md")
    if fmt in ("html", "both"):
        targets.append(root / "README.html")
    return targets


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    root = args.path.resolve()
    if not root.is_dir():
        print(f"Ошибка: папка не найдена: {root}", file=sys.stderr)
        return 1

    try:
        config = load_config(args.config)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        print(f"Ошибка конфига: {error}", file=sys.stderr)
        return 1

    description = args.description if args.description is not None else config.get("description", "")
    usage = args.usage or config.get("usage", DEFAULT_USAGE)
    sections = dict(config.get("sections", {}))

    if args.interactive:
        answers = run_wizard(defaults={"description": description, "usage": usage})
        description = answers["description"]
        usage = answers["usage"]
        sections.update(answers["sections"])

    info = scan_project(root)
    content = render_readme(info, description=description, usage=usage,
                            extra_sections=sections or None)

    if args.print_only:
        print(content)
        return 0

    targets = _target_files(root, args.format)
    existing = [t for t in targets if t.exists()]
    if existing and not args.force:
        names = ", ".join(t.name for t in existing)
        print(f"Ошибка: файл уже существует: {names}. Используйте --force.", file=sys.stderr)
        return 1

    for target in targets:
        if target.name == "README.md":
            write_readme(root, content, overwrite=True)
        else:
            target.write_text(markdown_to_html(content, title=info.name), encoding="utf-8")
        print(f"Готово: {target}")

    print(f"Файлов в проекте: {info.file_count}, основной язык: {info.primary_language}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

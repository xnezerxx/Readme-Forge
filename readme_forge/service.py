"""Логика readme-forge без графического интерфейса: её можно тестировать без окна."""

from __future__ import annotations

from pathlib import Path

from .core import render_readme, scan_project, write_readme
from .exporters import markdown_to_html


def generate_content(root: Path, description: str, usage: str, sections: dict[str, str] | None = None) -> str:
    info = scan_project(root)
    return render_readme(info, description=description, usage=usage, extra_sections=sections or None)


def parse_sections(raw: str) -> dict[str, str]:
    """Каждая строка вида 'Заголовок: текст' становится отдельным разделом."""
    sections: dict[str, str] = {}
    for line in raw.splitlines():
        title, sep, body = line.partition(":")
        if sep and title.strip():
            sections[title.strip()] = body.strip()
    return sections


def save_outputs(root: Path, content: str, title: str, fmt: str, force: bool) -> list[Path]:
    saved: list[Path] = []
    if fmt in ("md", "both"):
        saved.append(write_readme(root, content, overwrite=force))
    if fmt in ("html", "both"):
        target = root / "README.html"
        if target.exists() and not force:
            raise FileExistsError(f"Файл уже существует: {target}")
        target.write_text(markdown_to_html(content, title=title), encoding="utf-8")
        saved.append(target)
    return saved

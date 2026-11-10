"""Ядро readme-forge: сканирование проекта и сборка README.md."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .parsers import collect_manifest_deps

IGNORED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "env", "dist", "build", ".idea", ".vscode", ".mypy_cache", ".pytest_cache",
    "target", ".next", ".gradle",
}

LANGUAGE_MARKERS = {
    "Python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
    "JavaScript": ["package.json"],
    "TypeScript": ["tsconfig.json"],
    "Go": ["go.mod"],
    "Rust": ["Cargo.toml"],
    "Java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "Ruby": ["Gemfile"],
    "PHP": ["composer.json"],
    "C#": ["*.csproj", "*.sln"],
}

EXTENSION_LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
    ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".c": "C", ".kt": "Kotlin",
    ".swift": "Swift", ".dart": "Dart", ".sh": "Shell",
}

LICENSE_SIGNATURES = {
    "MIT": "MIT License",
    "Apache-2.0": "Apache License",
    "GPL-3.0": "GNU GENERAL PUBLIC LICENSE",
    "BSD-3-Clause": "BSD 3-Clause",
    "Unlicense": "This is free and unencumbered software",
}

REMOTE_PATTERN = re.compile(
    r"(?:git@|https?://)(?P<host>[^:/]+)[:/](?P<owner>[^/]+)/(?P<repo>[^/.\s]+?)(?:\.git)?$"
)


@dataclass
class ProjectInfo:
    name: str
    root: Path
    languages: dict[str, int] = field(default_factory=dict)
    primary_language: str = "Unknown"
    dependencies: list[str] = field(default_factory=list)
    license_id: str | None = None
    remote: tuple[str, str, str] | None = None
    has_tests: bool = False
    has_docker: bool = False
    has_ci: bool = False
    file_count: int = 0
    tree_lines: list[str] = field(default_factory=list)


def iter_files(root: Path, max_depth: int = 6) -> Iterable[Path]:
    """Обходит проект, пропуская служебные каталоги и слишком глубокие уровни."""
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name.lower())
        except PermissionError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name in IGNORED_DIRS or entry.name.startswith("."):
                    if entry.name != ".github":
                        continue
                if depth < max_depth:
                    stack.append((entry, depth + 1))
            elif entry.is_file():
                yield entry


def build_tree(root: Path, max_entries: int = 40) -> list[str]:
    """Строит текстовое дерево проекта в стиле `tree`."""
    lines: list[str] = [f"{root.name}/"]
    counter = 0

    def walk(directory: Path, prefix: str) -> None:
        nonlocal counter
        try:
            children = sorted(
                (c for c in directory.iterdir()
                 if c.name not in IGNORED_DIRS and not c.name.startswith(".")),
                key=lambda p: (p.is_file(), p.name.lower()),
            )
        except PermissionError:
            return
        for index, child in enumerate(children):
            if counter >= max_entries:
                lines.append(f"{prefix}└── ...")
                return
            last = index == len(children) - 1
            connector = "└── " if last else "├── "
            lines.append(f"{prefix}{connector}{child.name}{'/' if child.is_dir() else ''}")
            counter += 1
            if child.is_dir():
                extension = "    " if last else "│   "
                walk(child, prefix + extension)

    walk(root, "")
    return lines


def detect_languages(files: Iterable[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in files:
        language = EXTENSION_LANGUAGES.get(path.suffix.lower())
        if language:
            counts[language] = counts.get(language, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


def detect_primary_language(root: Path, languages: dict[str, int]) -> str:
    """Сначала смотрим на маркерные файлы, потом на статистику по расширениям."""
    for language, markers in LANGUAGE_MARKERS.items():
        for marker in markers:
            if "*" in marker:
                if any(root.glob(marker)):
                    return language
            elif (root / marker).exists():
                return language
    return next(iter(languages), "Unknown")


def read_dependencies(root: Path) -> list[str]:
    """Собирает имена зависимостей из манифестов разных экосистем."""
    return collect_manifest_deps(root)


def detect_license(root: Path) -> str | None:
    for candidate in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        path = root / candidate
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="ignore")
            for license_id, signature in LICENSE_SIGNATURES.items():
                if signature.lower() in text.lower():
                    return license_id
            return "Custom"
    return None


def read_git_remote(root: Path) -> tuple[str, str, str] | None:
    """Возвращает (host, owner, repo), если в проекте настроен origin."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    match = REMOTE_PATTERN.match(result.stdout.strip())
    if not match:
        return None
    return match["host"], match["owner"], match["repo"]


def scan_project(root: Path) -> ProjectInfo:
    root = root.resolve()
    files = list(iter_files(root))
    languages = detect_languages(files)
    names_lower = {f.name.lower() for f in files}
    relative_paths = {str(f.relative_to(root)).lower() for f in files}

    return ProjectInfo(
        name=root.name,
        root=root,
        languages=languages,
        primary_language=detect_primary_language(root, languages),
        dependencies=read_dependencies(root),
        license_id=detect_license(root),
        remote=read_git_remote(root),
        has_tests=any("test" in p for p in relative_paths),
        has_docker="dockerfile" in names_lower or "docker-compose.yml" in names_lower,
        has_ci=any(p.startswith(".github/workflows/") for p in relative_paths),
        file_count=len(files),
        tree_lines=build_tree(root),
    )


def make_badges(info: ProjectInfo) -> list[str]:
    badges: list[str] = []
    if info.remote:
        _, owner, repo = info.remote
        badges.append(
            f"![Stars](https://img.shields.io/github/stars/{owner}/{repo}?style=flat)"
        )
    if info.license_id:
        badges.append(
            f"![License](https://img.shields.io/badge/license-{info.license_id}-blue)"
        )
    if info.primary_language != "Unknown":
        badges.append(
            f"![Language](https://img.shields.io/badge/language-{info.primary_language.replace('#', 'sharp').replace('+', 'plus')}-informational)"
        )
    if info.has_ci:
        badges.append("![CI](https://img.shields.io/badge/CI-configured-brightgreen)")
    return badges


def render_section(title: str, body: list[str]) -> list[str]:
    if not body or all(not line.strip() for line in body):
        return []
    return [f"## {title}", "", *body, ""]


def render_readme(info: ProjectInfo, description: str, usage: str,
                  extra_sections: dict[str, str] | None = None) -> str:
    lines: list[str] = [f"# {info.name}", ""]

    badges = make_badges(info)
    if badges:
        lines += [" ".join(badges), ""]

    lines += [description or f"Проект на {info.primary_language}.", ""]

    languages_body = [
        f"- **{language}**: {count} файл(ов)" for language, count in info.languages.items()
    ]
    lines += render_section("Технологии", languages_body)

    lines += render_section(
        "Зависимости",
        [f"- `{dep}`" for dep in info.dependencies[:30]],
    )

    install_body = []
    if info.remote:
        host, owner, repo = info.remote
        install_body += [
            "```bash",
            f"git clone https://{host}/{owner}/{repo}.git",
            f"cd {repo}",
            "```",
        ]
    lines += render_section("Установка", install_body)

    lines += render_section("Использование", ["```bash", usage, "```"])

    tree_body = ["```text", *info.tree_lines, "```"]
    lines += render_section("Структура проекта", tree_body)

    for title, content in (extra_sections or {}).items():
        lines += render_section(title, [content])

    license_body = (
        [f"Проект распространяется по лицензии **{info.license_id}**."]
        if info.license_id else
        ["Лицензия не указана. Добавьте файл LICENSE, чтобы определить условия использования."]
    )
    lines += render_section("Лицензия", license_body)

    return "\n".join(lines).rstrip() + "\n"


def write_readme(root: Path, content: str, overwrite: bool = False) -> Path:
    target = root / "README.md"
    if target.exists() and not overwrite:
        raise FileExistsError(f"Файл уже существует: {target}. Используйте --force.")
    target.write_text(content, encoding="utf-8")
    return target

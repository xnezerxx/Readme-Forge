"""Чтение зависимостей из манифестов разных экосистем."""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

_NAME_SPLIT = re.compile(r"[<>=!~\[; ]")


def package_name(spec: str) -> str:
    """Из строки вида 'requests>=2.31' достаёт 'requests'."""
    return _NAME_SPLIT.split(spec.strip(), maxsplit=1)[0]


def _load_toml(path: Path) -> dict:
    if tomllib is None or not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}


def requirements_txt(root: Path) -> list[str]:
    path = root / "requirements.txt"
    if not path.exists():
        return []
    deps = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            deps.append(package_name(line))
    return deps


def pyproject_toml(root: Path) -> list[str]:
    data = _load_toml(root / "pyproject.toml")
    deps = list(data.get("project", {}).get("dependencies", []))
    poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    names = [package_name(d) for d in deps]
    names += [name for name in poetry if name.lower() != "python"]
    return names


def package_json(root: Path) -> list[str]:
    path = root / "package.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return list(data.get("dependencies", {}).keys())


def cargo_toml(root: Path) -> list[str]:
    data = _load_toml(root / "Cargo.toml")
    return list(data.get("dependencies", {}).keys())


def go_mod(root: Path) -> list[str]:
    path = root / "go.mod"
    if not path.exists():
        return []
    deps: list[str] = []
    in_block = False
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_block = True
            continue
        if in_block and stripped == ")":
            in_block = False
            continue
        if in_block or stripped.startswith("require "):
            body = stripped[len("require "):] if stripped.startswith("require ") else stripped
            parts = body.split()
            if parts and not parts[0].startswith("//"):
                deps.append(parts[0])
    return deps


def gemfile(root: Path) -> list[str]:
    path = root / "Gemfile"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    return re.findall(r"^\s*gem\s+['\"]([^'\"]+)['\"]", text, flags=re.MULTILINE)


def composer_json(root: Path) -> list[str]:
    path = root / "composer.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [
        name for name in data.get("require", {})
        if name != "php" and not name.startswith("ext-")
    ]


PARSERS = (
    requirements_txt,
    pyproject_toml,
    package_json,
    cargo_toml,
    go_mod,
    gemfile,
    composer_json,
)


def collect_manifest_deps(root: Path) -> list[str]:
    """Возвращает отсортированный список уникальных зависимостей проекта."""
    found: set[str] = set()
    for parser in PARSERS:
        found.update(name for name in parser(root) if name)
    return sorted(found, key=str.lower)

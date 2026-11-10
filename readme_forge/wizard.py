"""Интерактивный мастер: задаёт вопросы и собирает настройки README."""

from __future__ import annotations

from typing import Callable


def run_wizard(
    defaults: dict | None = None,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
) -> dict:
    defaults = defaults or {}

    def ask(question: str, default: str = "") -> str:
        suffix = f" [{default}]" if default else ""
        answer = input_fn(f"{question}{suffix}: ").strip()
        return answer or default

    print_fn("Мастер создания README. Enter без ввода принимает значение в скобках.")
    description = ask("Описание проекта", defaults.get("description", ""))
    usage = ask("Команда запуска", defaults.get("usage", "python main.py"))

    sections: dict[str, str] = {}
    print_fn("Дополнительные разделы. Пустое название завершает ввод.")
    while True:
        title = input_fn("Название раздела: ").strip()
        if not title:
            break
        sections[title] = input_fn(f"Текст раздела «{title}»: ").strip()

    return {"description": description, "usage": usage, "sections": sections}

"""Графический интерфейс readme-forge на tkinter (входит в стандартный Python)."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .service import generate_content, parse_sections, save_outputs

PALETTE = {
    "bg": "#f4f6fb",
    "card": "#ffffff",
    "accent": "#5b6cff",
    "accent_hover": "#4a5bee",
    "text": "#1d2233",
    "muted": "#7a8099",
    "border": "#dfe3ee",
    "success": "#2fa36b",
    "error": "#d64545",
}

FORMATS = [("Markdown (README.md)", "md"), ("HTML (README.html)", "html"), ("Оба формата", "both")]


# ---------- интерфейс ----------

def add_edit_menu(widget: tk.Widget) -> None:
    """Контекстное меню по правой кнопке мыши: вырезать, копировать, вставить."""
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(label="Вырезать", command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="Копировать", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="Вставить", command=lambda: widget.event_generate("<<Paste>>"))

    def show(event: tk.Event) -> None:
        widget.focus_set()
        menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", show)  # правая кнопка (Windows, Linux)
    widget.bind("<Button-2>", show)  # правая кнопка (macOS)


def attach_edit_menus(parent: tk.Widget) -> None:
    for child in parent.winfo_children():
        if child.winfo_class() in ("Entry", "TEntry", "Text"):
            add_edit_menu(child)
        attach_edit_menus(child)


class ReadmeForgeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"readme-forge {__version__}")
        self.geometry("1120x720")
        self.minsize(940, 620)
        self.configure(bg=PALETTE["bg"])

        self.content: str = ""
        self.path_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.usage_var = tk.StringVar(value="python main.py")
        self.format_var = tk.StringVar(value="md")
        self.force_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Выберите папку проекта и нажмите «Создать»")
        self.status_color = PALETTE["muted"]

        self._setup_styles()
        self._build()

    def _setup_styles(self) -> None:
        p = PALETTE
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Card.TFrame", background=p["card"])
        style.configure("Title.TLabel", background=p["bg"], foreground=p["text"], font=("Segoe UI", 20, "bold"))
        style.configure("Sub.TLabel", background=p["bg"], foreground=p["muted"], font=("Segoe UI", 10))
        style.configure("Field.TLabel", background=p["card"], foreground=p["text"], font=("Segoe UI", 10, "bold"))
        style.configure("Hint.TLabel", background=p["card"], foreground=p["muted"], font=("Segoe UI", 9))
        style.configure("Card.TRadiobutton", background=p["card"], foreground=p["text"], font=("Segoe UI", 10))
        style.configure("Card.TCheckbutton", background=p["card"], foreground=p["text"], font=("Segoe UI", 10))
        style.configure("Accent.TButton", background=p["accent"], foreground="white",
                        font=("Segoe UI", 10, "bold"), padding=(18, 9), borderwidth=0)
        style.map("Accent.TButton", background=[("active", p["accent_hover"]), ("disabled", p["border"])])
        style.configure("Ghost.TButton", background=p["card"], foreground=p["accent"],
                        font=("Segoe UI", 10), padding=(12, 8), bordercolor=p["border"])
        style.map("Ghost.TButton", background=[("active", p["bg"])])
        style.configure("Status.TLabel", background=p["bg"], font=("Segoe UI", 9))

    def _build(self) -> None:
        p = PALETTE
        outer = tk.Frame(self, bg=p["bg"])
        outer.pack(fill="both", expand=True, padx=24, pady=20)

        ttk.Label(outer, text="readme-forge", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="README для вашего проекта за несколько кликов",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 16))

        body = tk.Frame(outer, bg=p["bg"])
        body.pack(fill="both", expand=True)

        form = ttk.Frame(body, style="Card.TFrame", padding=22)
        form.pack(side="left", fill="y")
        self._build_form(form)

        preview = ttk.Frame(body, style="Card.TFrame", padding=22)
        preview.pack(side="left", fill="both", expand=True, padx=(18, 0))
        self._build_preview(preview)

        status = ttk.Label(outer, textvariable=self.status_var, style="Status.TLabel")
        status.pack(anchor="w", pady=(14, 0))
        self.status_label = status
        self._set_status(self.status_var.get(), p["muted"])

    def _build_form(self, form: ttk.Frame) -> None:
        form.columnconfigure(0, weight=1)
        ttk.Label(form, text="Папка проекта", style="Field.TLabel").grid(row=0, column=0, sticky="w")
        row = ttk.Frame(form, style="Card.TFrame")
        row.grid(row=1, column=0, sticky="ew", pady=(4, 14))
        row.columnconfigure(0, weight=1)
        ttk.Entry(row, textvariable=self.path_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(row, text="Обзор…", style="Ghost.TButton", command=self._browse).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(form, text="Описание", style="Field.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.description_var, width=44).grid(row=3, column=0, sticky="ew", pady=(4, 14))

        ttk.Label(form, text="Команда запуска", style="Field.TLabel").grid(row=4, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.usage_var).grid(row=5, column=0, sticky="ew", pady=(4, 14))

        ttk.Label(form, text="Дополнительные разделы", style="Field.TLabel").grid(row=6, column=0, sticky="w")
        ttk.Label(form, text="Формат: Заголовок: текст (по одному на строку)",
                  style="Hint.TLabel").grid(row=7, column=0, sticky="w")
        self.sections_text = tk.Text(form, height=5, width=44, relief="solid", bd=1,
                                     highlightthickness=0, font=("Segoe UI", 10),
                                     bg="#fbfcfe", fg=PALETTE["text"], wrap="word")
        self.sections_text.grid(row=8, column=0, sticky="ew", pady=(4, 14))

        ttk.Label(form, text="Формат результата", style="Field.TLabel").grid(row=9, column=0, sticky="w")
        for index, (label, value) in enumerate(FORMATS):
            ttk.Radiobutton(form, text=label, value=value, variable=self.format_var,
                            style="Card.TRadiobutton").grid(row=10 + index, column=0, sticky="w", pady=1)

        ttk.Checkbutton(form, text="Перезаписать существующие файлы", variable=self.force_var,
                        style="Card.TCheckbutton").grid(row=14, column=0, sticky="w", pady=(12, 14))

        buttons = ttk.Frame(form, style="Card.TFrame")
        buttons.grid(row=15, column=0, sticky="ew")
        ttk.Button(buttons, text="Создать предпросмотр", style="Accent.TButton",
                   command=self._generate).pack(fill="x")
        ttk.Button(buttons, text="Сохранить файлы", style="Ghost.TButton",
                   command=self._save).pack(fill="x", pady=(10, 0))
        attach_edit_menus(form)

    def _build_preview(self, preview: ttk.Frame) -> None:
        header = ttk.Frame(preview, style="Card.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Предпросмотр", style="Field.TLabel").pack(side="left")
        ttk.Button(header, text="Копировать", style="Ghost.TButton",
                   command=self._copy).pack(side="right")

        frame = tk.Frame(preview, bg=PALETTE["border"], bd=0)
        frame.pack(fill="both", expand=True, pady=(12, 0))
        self.preview_text = tk.Text(frame, wrap="word", font=("Consolas", 10), relief="flat",
                                    bg="#fbfcfe", fg=PALETTE["text"], padx=14, pady=12,
                                    highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=scroll.set)
        self.preview_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.preview_text.insert("1.0", "Здесь появится результат. Выберите папку и нажмите «Создать предпросмотр».")
        self.preview_text.configure(state="disabled")

    # ----- действия -----

    def _set_status(self, message: str, color: str) -> None:
        self.status_var.set(message)
        self.status_label.configure(foreground=color)

    def _browse(self) -> None:
        folder = filedialog.askdirectory(title="Выберите папку проекта")
        if folder:
            self.path_var.set(folder)

    def _project_root(self) -> Path | None:
        raw = self.path_var.get().strip()
        if not raw:
            messagebox.showwarning("readme-forge", "Сначала выберите папку проекта.")
            return None
        root = Path(raw).expanduser().resolve()
        if not root.is_dir():
            messagebox.showerror("readme-forge", f"Папка не найдена:\n{root}")
            return None
        return root

    def _generate(self) -> None:
        root = self._project_root()
        if root is None:
            return
        self.content = generate_content(
            root,
            description=self.description_var.get().strip(),
            usage=self.usage_var.get().strip() or "python main.py",
            sections=parse_sections(self.sections_text.get("1.0", "end")),
        )
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", self.content)
        self.preview_text.configure(state="disabled")
        self._set_status("Предпросмотр готов. Проверьте текст и сохраните файлы.", PALETTE["success"])

    def _save(self) -> None:
        if not self.content:
            self._generate()
            if not self.content:
                return
        root = self._project_root()
        if root is None:
            return
        try:
            saved = save_outputs(root, self.content, root.name, self.format_var.get(),
                                 force=self.force_var.get())
        except FileExistsError as error:
            self._set_status("Файл уже существует. Включите перезапись или выберите другой формат.", PALETTE["error"])
            messagebox.showerror("readme-forge", str(error))
            return
        names = ", ".join(path.name for path in saved)
        self._set_status(f"Сохранено: {names}", PALETTE["success"])
        messagebox.showinfo("readme-forge", f"Готово!\n\n" + "\n".join(str(p) for p in saved))

    def _copy(self) -> None:
        if not self.content:
            self._set_status("Сначала создайте предпросмотр.", PALETTE["error"])
            return
        self.clipboard_clear()
        self.clipboard_append(self.content)
        self._set_status("Текст скопирован в буфер обмена.", PALETTE["success"])


def main() -> None:
    ReadmeForgeApp().mainloop()


if __name__ == "__main__":
    main()

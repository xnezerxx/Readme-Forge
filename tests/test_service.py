import tempfile
import unittest
from pathlib import Path

from readme_forge.service import generate_content, parse_sections, save_outputs


class TestService(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "demo"
        self.root.mkdir()
        (self.root / "app.py").write_text("print(1)\n", encoding="utf-8")
        (self.root / "LICENSE").write_text("MIT License", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_parse_sections_multiline_and_skips_invalid(self):
        raw = "Установка: pip install x\nбез двоеточия\n: пустой заголовок\nRoadmap: v1 -> v2"
        self.assertEqual(parse_sections(raw), {"Установка": "pip install x", "Roadmap": "v1 -> v2"})

    def test_generate_content_contains_inputs(self):
        content = generate_content(self.root, "Описание", "python app.py", {"Заметки": "ok"})
        self.assertIn("Описание", content)
        self.assertIn("python app.py", content)
        self.assertIn("## Заметки", content)
        self.assertIn("MIT", content)

    def test_save_md_and_html(self):
        saved = save_outputs(self.root, "# T\n", "T", "both", force=False)
        self.assertEqual({p.name for p in saved}, {"README.md", "README.html"})
        self.assertIn("<h1>T</h1>", (self.root / "README.html").read_text(encoding="utf-8"))

    def test_save_refuses_existing_without_force(self):
        (self.root / "README.html").write_text("old", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            save_outputs(self.root, "# T\n", "T", "html", force=False)
        save_outputs(self.root, "# T\n", "T", "html", force=True)
        self.assertIn("<h1>T</h1>", (self.root / "README.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

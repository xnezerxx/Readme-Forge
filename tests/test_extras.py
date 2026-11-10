import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from readme_forge.cli import main
from readme_forge.exporters import inline, markdown_to_html
from readme_forge.parsers import (
    cargo_toml,
    collect_manifest_deps,
    composer_json,
    gemfile,
    go_mod,
    package_name,
    pyproject_toml,
)
from readme_forge.wizard import run_wizard


class TmpCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, content=""):
        (self.root / name).write_text(content, encoding="utf-8")


class TestParsers(TmpCase):
    def test_package_name(self):
        self.assertEqual(package_name("requests>=2.31"), "requests")
        self.assertEqual(package_name("uvicorn[standard]==0.30"), "uvicorn")

    def test_pyproject_pep621_and_poetry(self):
        self.write("pyproject.toml", '[project]\nname="x"\ndependencies=["httpx>=0.27", "rich"]\n'
                   '[tool.poetry.dependencies]\npython="^3.11"\nattrs="*"\n')
        self.assertEqual(pyproject_toml(self.root), ["httpx", "rich", "attrs"])

    def test_cargo(self):
        self.write("Cargo.toml", '[dependencies]\nserde = "1"\ntokio = { version = "1" }\n')
        self.assertEqual(cargo_toml(self.root), ["serde", "tokio"])

    def test_go_mod_block_and_single_line(self):
        self.write("go.mod", "module x\n\ngo 1.22\n\nrequire github.com/a/b v1.0.0\n\n"
                   "require (\n\tgithub.com/c/d v2.0.0 // indirect\n\t// comment\n)\n")
        self.assertEqual(go_mod(self.root), ["github.com/a/b", "github.com/c/d"])

    def test_gemfile(self):
        self.write("Gemfile", "source 'https://rubygems.org'\ngem 'rails'\n  gem \"puma\", '~> 6'\n")
        self.assertEqual(gemfile(self.root), ["rails", "puma"])

    def test_composer_skips_php_and_extensions(self):
        self.write("composer.json", json.dumps({"require": {"php": "^8", "ext-json": "*", "monolog/monolog": "^3"}}))
        self.assertEqual(composer_json(self.root), ["monolog/monolog"])

    def test_collect_merges_ecosystems_uniquely(self):
        self.write("requirements.txt", "requests\nrich\n")
        self.write("pyproject.toml", '[project]\ndependencies=["rich>=13"]\n')
        self.assertEqual(collect_manifest_deps(self.root), ["requests", "rich"])


class TestExporters(unittest.TestCase):
    def test_inline_escapes_html(self):
        self.assertEqual(inline("<script>"), "&lt;script&gt;")

    def test_inline_formats_code_bold_link(self):
        out = inline("Use `pip` and **bold** see [site](https://x.dev)")
        self.assertIn("<code>pip</code>", out)
        self.assertIn("<strong>bold</strong>", out)
        self.assertIn('<a href="https://x.dev">site</a>', out)

    def test_full_page_structure(self):
        md = "# Title\n\nText line\n\n- one\n- two\n\n```bash\necho <hi>\n```\n"
        page = markdown_to_html(md, title="T")
        self.assertIn("<h1>Title</h1>", page)
        self.assertIn("<ul>", page)
        self.assertIn("<li>two</li>", page)
        self.assertIn("echo &lt;hi&gt;", page)
        self.assertIn("<title>T</title>", page)
        self.assertNotIn("__BODY__", page)


class TestWizard(unittest.TestCase):
    def test_wizard_collects_answers_and_defaults(self):
        answers = iter(["Мой проект", "", "Установка", "pip install x", ""])
        result = run_wizard(
            defaults={"usage": "python app.py"},
            input_fn=lambda _prompt: next(answers),
            print_fn=lambda _msg: None,
        )
        self.assertEqual(result["description"], "Мой проект")
        self.assertEqual(result["usage"], "python app.py")
        self.assertEqual(result["sections"], {"Установка": "pip install x"})


class TestCli(TmpCase):
    def test_html_and_md_both(self):
        (self.root / "app.py").write_text("print(1)\n", encoding="utf-8")
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main([str(self.root), "-d", "Тест", "--format", "both"])
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "README.md").exists())
        self.assertIn("<h1>", (self.root / "README.html").read_text(encoding="utf-8"))

    def test_refuses_overwrite_without_force(self):
        (self.root / "README.md").write_text("old", encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            code = main([str(self.root)])
        self.assertEqual(code, 1)
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), "old")


if __name__ == "__main__":
    unittest.main()

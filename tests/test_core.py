import json
import tempfile
import unittest
from pathlib import Path

from readme_forge.core import (
    build_tree,
    detect_license,
    detect_primary_language,
    read_dependencies,
    render_readme,
    scan_project,
    write_readme,
)


class ProjectFixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "demo"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, relative: str, content: str = "") -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class TestDetection(ProjectFixture):
    def test_primary_language_from_marker(self):
        self.write("requirements.txt", "requests>=2\n")
        self.write("app.py", "print('hi')\n")
        languages = {"Python": 1}
        self.assertEqual(detect_primary_language(self.root, languages), "Python")

    def test_primary_language_falls_back_to_extensions(self):
        self.write("main.kt", "fun main() {}\n")
        self.assertEqual(detect_primary_language(self.root, {"Kotlin": 1}), "Kotlin")

    def test_license_detected_mit(self):
        self.write("LICENSE", "MIT License\n\nCopyright (c) 2026")
        self.assertEqual(detect_license(self.root), "MIT")

    def test_license_custom_when_unknown_text(self):
        self.write("LICENSE", "Some proprietary terms")
        self.assertEqual(detect_license(self.root), "Custom")

    def test_no_license(self):
        self.assertIsNone(detect_license(self.root))

    def test_requirements_parsed_without_versions_and_comments(self):
        self.write(
            "requirements.txt",
            "# comment\nrequests>=2.31\nrich==13.7.0  # pretty output\n-e .\nclick\n",
        )
        self.assertEqual(read_dependencies(self.root), ["click", "requests", "rich"])

    def test_package_json_dependencies(self):
        self.write(
            "package.json",
            json.dumps({"dependencies": {"react": "^18", "axios": "^1"}}),
        )
        self.assertEqual(read_dependencies(self.root), ["axios", "react"])

    def test_broken_package_json_is_ignored(self):
        self.write("package.json", "{not json")
        self.assertEqual(read_dependencies(self.root), [])


class TestTreeAndScan(ProjectFixture):
    def test_tree_skips_ignored_directories(self):
        self.write("src/main.py", "")
        self.write("node_modules/junk.js", "")
        self.write(".git/config", "")
        tree = "\n".join(build_tree(self.root))
        self.assertIn("src/", tree)
        self.assertNotIn("node_modules", tree)
        self.assertNotIn(".git", tree)

    def test_scan_detects_ci_and_tests(self):
        self.write(".github/workflows/ci.yml", "name: ci\n")
        self.write("tests/test_a.py", "")
        info = scan_project(self.root)
        self.assertTrue(info.has_ci)
        self.assertTrue(info.has_tests)
        self.assertFalse(info.has_docker)

    def test_scan_counts_files(self):
        self.write("a.py", "")
        self.write("b.py", "")
        self.assertEqual(scan_project(self.root).file_count, 2)


class TestRendering(ProjectFixture):
    def test_readme_contains_core_sections(self):
        self.write("LICENSE", "MIT License")
        self.write("app.py", "")
        info = scan_project(self.root)
        content = render_readme(info, description="Тестовый проект", usage="python app.py")
        for heading in ("# demo", "## Технологии", "## Использование",
                        "## Структура проекта", "## Лицензия"):
            self.assertIn(heading, content)
        self.assertIn("python app.py", content)
        self.assertIn("MIT", content)

    def test_extra_sections_are_appended(self):
        info = scan_project(self.root)
        content = render_readme(info, "d", "run", {"Roadmap": "- v1.0"})
        self.assertIn("## Roadmap", content)

    def test_missing_license_gets_hint(self):
        info = scan_project(self.root)
        content = render_readme(info, "d", "run")
        self.assertIn("Лицензия не указана", content)

    def test_write_refuses_overwrite_without_force(self):
        self.write("README.md", "old")
        with self.assertRaises(FileExistsError):
            write_readme(self.root, "new")
        write_readme(self.root, "new", overwrite=True)
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), "new")


if __name__ == "__main__":
    unittest.main()

import unittest


class TestGuiImport(unittest.TestCase):
    """Проверяет, что окно собирается, когда доступен tkinter и дисплей."""

    @classmethod
    def setUpClass(cls):
        try:
            import tkinter
            cls.root = tkinter.Tk()
            cls.root.withdraw()
        except Exception as error:  # нет tkinter или дисплея
            raise unittest.SkipTest(f"GUI недоступен: {error}")

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_app_builds_and_generates_preview(self):
        import tempfile
        from pathlib import Path
        from readme_forge.gui import ReadmeForgeApp

        app = ReadmeForgeApp()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "main.py").write_text("print(1)\n", encoding="utf-8")
                app.path_var.set(tmp)
                app.description_var.set("GUI test")
                app._generate()
                self.assertIn("GUI test", app.content)
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()

"""Ensure every import declared by the Streamlit entry point resolves locally."""

import ast
import importlib
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import risk_logic
import riskradar_db


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app.py"


class AppImportTests(unittest.TestCase):
    def test_all_app_imports_resolve_and_risk_logic_is_project_local(self):
        syntax_tree = ast.parse(APP_PATH.read_text(encoding="utf-8"), filename=str(APP_PATH))

        for node in ast.walk(syntax_tree):
            if isinstance(node, ast.Import):
                for imported in node.names:
                    with self.subTest(module=imported.name):
                        importlib.import_module(imported.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    self.fail(f"Relative imports are not expected in app.py (line {node.lineno}).")
                module = importlib.import_module(node.module)
                for imported in node.names:
                    if imported.name == "*":
                        self.fail(f"Wildcard imports are not allowed in app.py (line {node.lineno}).")
                    with self.subTest(module=node.module, name=imported.name):
                        self.assertTrue(
                            hasattr(module, imported.name),
                            f"app.py imports missing name {imported.name!r} from {node.module!r}",
                        )

        import risk_logic

        self.assertEqual(Path(risk_logic.__file__).resolve(), PROJECT_ROOT / "risk_logic.py")
        self.assertTrue(callable(risk_logic.group_risks_by_cell))

    def test_app_recovers_if_streamlit_has_a_stale_logic_module(self):
        del risk_logic.group_risks_by_cell
        try:
            with (
                patch.object(riskradar_db, "initialize_db"),
                patch.object(riskradar_db, "seed_sample_data"),
                patch.object(riskradar_db, "list_projects", return_value=[]),
                patch.object(riskradar_db, "list_risks", return_value=[]),
            ):
                app = AppTest.from_file(str(APP_PATH)).run(timeout=20)

            self.assertEqual(len(app.exception), 0)
            self.assertTrue(callable(risk_logic.group_risks_by_cell))
        finally:
            if not hasattr(risk_logic, "group_risks_by_cell"):
                importlib.reload(risk_logic)


if __name__ == "__main__":
    unittest.main()

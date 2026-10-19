"""Ensure every import declared by the Streamlit entry point resolves locally."""

import ast
import importlib
import subprocess
import sys
import unittest
from pathlib import Path

import risk_logic


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

        self.assertEqual(Path(risk_logic.__file__).resolve(), PROJECT_ROOT / "risk_logic.py")
        self.assertTrue(callable(risk_logic.group_risks_by_cell))

    def test_stale_module_is_reloaded_when_an_export_is_missing(self):
        script = "\n".join((
            "import risk_logic, riskradar_db",
            "from runtime_imports import ensure_module_exports",
            "del risk_logic.group_risks_by_cell",
            "del riskradar_db.DatabaseError",
            "ensure_module_exports(risk_logic, ('group_risks_by_cell',))",
            "ensure_module_exports(riskradar_db, ('DatabaseError', 'DuplicateRecordError'))",
            "assert callable(risk_logic.group_risks_by_cell)",
            "assert issubclass(riskradar_db.DuplicateRecordError, riskradar_db.DatabaseError)",
        ))
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

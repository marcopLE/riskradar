"""Streamlit AppTest coverage using an isolated temporary SQLite database."""

import tempfile
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_RUNTIME_DIR = PROJECT_ROOT / ".tmp" / "streamlit-test"
for environment_variable, directory in (
    ("STREAMLIT_CONFIG_DIR", TEST_RUNTIME_DIR / "config"),
    ("XDG_CACHE_HOME", TEST_RUNTIME_DIR / "cache"),
    ("TMPDIR", TEST_RUNTIME_DIR / "tmp"),
):
    directory.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(environment_variable, str(directory))

import riskradar_db
import risk_logic
from riskradar_db import DatabaseOperationError
from risk_logic import RiskThresholds
from streamlit.testing.v1 import AppTest


APP_PATH = PROJECT_ROOT / "app.py"


class RiskRadarAppTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(dir=PROJECT_ROOT)
        self.db_path = Path(self.tempdir.name) / "app-test.db"
        self.originals = {
            name: getattr(riskradar_db, name)
            for name in ("initialize_db", "seed_sample_data", "list_projects", "list_risks", "add_project", "add_risk")
        }

        def initialize_db():
            return self.originals["initialize_db"](self.db_path)

        def seed_sample_data():
            return self.originals["seed_sample_data"](self.db_path)

        def list_projects():
            return self.originals["list_projects"](self.db_path)

        def list_risks(project_id=None):
            return self.originals["list_risks"](project_id, self.db_path)

        def add_project(name, description):
            return self.originals["add_project"](name, description, self.db_path)

        def add_risk(project_id, title, description, probability, impact):
            return self.originals["add_risk"](
                project_id, title, description, probability, impact, self.db_path
            )

        self.patches = [
            patch.object(riskradar_db, "initialize_db", new=initialize_db),
            patch.object(riskradar_db, "seed_sample_data", new=seed_sample_data),
            patch.object(riskradar_db, "list_projects", new=list_projects),
            patch.object(riskradar_db, "list_risks", new=list_risks),
            patch.object(riskradar_db, "add_project", new=add_project),
            patch.object(riskradar_db, "add_risk", new=add_risk),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.tempdir.cleanup()

    def run_app(self):
        return AppTest.from_file(str(APP_PATH)).run(timeout=20)

    def test_dashboard_starts_and_warns_about_cloud_persistence(self):
        app = self.run_app()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual([tab.label for tab in app.tabs], ["Übersicht", "Projekte", "Risiken", "Risikomatrix"])
        self.assertTrue(any("nicht dauerhaft" in item.value for item in app.info))
        self.assertTrue(any("Logo-Platzhalter" in item.value for item in app.markdown))
        self.assertTrue(any("IT-Projektrisiken · Portfolio-Übersicht" in item.value for item in app.markdown))
        self.assertTrue(any("Kein offizielles adesso-Logo" in item.value for item in app.caption))
        self.assertEqual(
            [metric.label for metric in app.metric],
            ["Projekte", "Risiken", "Kritische Risiken", "Empfohlene Maßnahmen"],
        )
        matrix_buttons = [
            button for button in app.button
            if button.key and button.key.startswith("matrix_cell_")
        ]
        self.assertEqual(len(matrix_buttons), 25)
        self.assertTrue(any("Auswirkung →" in item.value for item in app.markdown))
        app.button(key="matrix_cell_5_5").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any(
            "Feld: Wahrscheinlichkeit 5 × Auswirkung 5" in item.value
            for item in app.markdown
        ))

    def test_recommended_measures_can_be_selected_and_are_disclosed(self):
        app = self.run_app()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("nicht mit KI erzeugt" in item.value for item in app.info))
        selector = app.selectbox(key="recommended_measures_risk")
        security_risk = next(
            option for option in selector.options
            if "Fehlkonfiguration von Zugriffsrechten" in option
        )
        selector.set_value(security_risk).run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Sicherheitsrisiken" in item.value for item in app.markdown))
        self.assertTrue(any("Sicherheitsprüfung" in item.value for item in app.markdown))

    def test_matrix_legend_uses_configured_thresholds(self):
        configured = RiskThresholds(low_max=4, medium_max=10)
        with patch.object(risk_logic, "DEFAULT_RISK_THRESHOLDS", configured):
            app = self.run_app()

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any(
            "Niedrig (Score 1–4)" in item.value
            and "Mittel (5–10)" in item.value
            and "Hoch (11–25)" in item.value
            for item in app.caption
        ))

        with patch.object(
            risk_logic, "DEFAULT_RISK_THRESHOLDS", RiskThresholds(low_max=24, medium_max=25)
        ):
            boundary_app = self.run_app()
        self.assertEqual(len(boundary_app.exception), 0)
        self.assertTrue(any(
            "Hoch (keine möglichen Scores)" in item.value
            and "26–25" not in item.value
            for item in boundary_app.caption
        ))

    def test_project_form_creates_project(self):
        app = self.run_app()
        app.text_input[0].set_value("AppTest-Projekt")
        app.text_area[0].set_value("Fiktives Integrationstestprojekt")
        app.button(key="FormSubmitter:project_form-Projekt anlegen").click().run()

        created = self.originals["list_projects"](self.db_path)
        self.assertTrue(any(project["name"] == "AppTest-Projekt" for project in created))
        self.assertEqual(len(app.exception), 0)

    def test_blank_project_form_shows_validation_feedback(self):
        app = self.run_app()
        app.button(key="FormSubmitter:project_form-Projekt anlegen").click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Projektname" in item.value for item in app.error))
        self.assertEqual(len(self.originals["list_projects"](self.db_path)), 5)

    def test_database_startup_error_is_reported_in_the_ui(self):
        def fail_initialization():
            raise DatabaseOperationError("simulierter SQLite-Ausfall")

        with patch.object(riskradar_db, "initialize_db", new=fail_initialization):
            app = self.run_app()

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("simulierter SQLite-Ausfall" in item.value for item in app.error))

    def test_risk_form_saves_rating_and_shows_duplicate_feedback(self):
        app = self.run_app()
        cloud_option = next(
            option for option in app.selectbox(key="risk_project_selector").options
            if option.endswith("Cloud-Modernisierung")
        )
        app.selectbox(key="risk_project_selector").set_value(cloud_option)
        app.text_input[1].set_value("AppTest-Risiko")
        app.text_area[1].set_value("Fiktives Risiko für einen Integrationstest")
        app.select_slider[0].set_value(5)
        app.select_slider[1].set_value(4)
        app.button(key="FormSubmitter:risk_form-Risiko speichern").click().run()

        saved = [risk for risk in self.originals["list_risks"](None, self.db_path) if risk["title"] == "AppTest-Risiko"]
        self.assertEqual(len(saved), 1)
        self.assertEqual((saved[0]["probability"], saved[0]["impact"]), (5, 4))

        app.selectbox(key="risk_project_selector").set_value(cloud_option)
        app.text_input[1].set_value("AppTest-Risiko")
        app.button(key="FormSubmitter:risk_form-Risiko speichern").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("bereits ein Risiko" in item.value for item in app.error))
        self.assertEqual(len([risk for risk in self.originals["list_risks"](None, self.db_path) if risk["title"] == "AppTest-Risiko"]), 1)

    def test_casefold_duplicate_legacy_projects_have_distinct_filter_options(self):
        self.originals["initialize_db"](self.db_path)
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            connection.execute("DROP INDEX idx_projects_name_nocase")
            connection.execute("INSERT INTO projects (name) VALUES (?)", ("Legacy Filter",))
            first_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
            connection.execute("INSERT INTO projects (name) VALUES (?)", ("legacy filter",))
            second_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
            connection.execute(
                "INSERT INTO risks (project_id, title, probability, impact) VALUES (?, ?, 3, 3)",
                (first_id, "Nur erstes Projekt"),
            )

        app = self.run_app()
        first_label, second_label = f"[{first_id}] Legacy Filter", f"[{second_id}] legacy filter"
        self.assertIn(first_label, app.selectbox(key="risk_filter").options)
        self.assertIn(second_label, app.selectbox(key="risk_filter").options)
        self.assertIn(first_label, app.selectbox(key="matrix_project_filter").options)
        self.assertIn(second_label, app.selectbox(key="matrix_project_filter").options)

        app.selectbox(key="risk_filter").set_value(second_label).run()
        self.assertTrue(any("Für diese Auswahl sind keine Risiken vorhanden" in item.value for item in app.info))
        app.selectbox(key="matrix_project_filter").set_value(second_label).run()
        self.assertTrue(any("Für den gewählten Projektfilter sind keine Risiken vorhanden" in item.value for item in app.info))


if __name__ == "__main__":
    unittest.main()

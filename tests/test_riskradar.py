import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import riskradar_db
from risk_logic import (
    RiskInputError,
    RiskThresholds,
    calculate_score,
    group_risks_by_cell,
    risk_level,
)
from riskradar_db import (
    DatabaseOperationError,
    DataValidationError,
    DuplicateRecordError,
    add_project,
    add_risk,
    initialize_db,
    list_projects,
    list_risks,
    seed_sample_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RiskLogicTests(unittest.TestCase):
    def test_score_boundaries_and_integer_validation(self):
        self.assertEqual(calculate_score(1, 1), 1)
        self.assertEqual(calculate_score(5, 5), 25)
        for values in ((0, 2), (6, 2), (3, 0), (3, 6), (True, 2), (2.5, 2), ("2", 2)):
            with self.subTest(values=values), self.assertRaises(RiskInputError):
                calculate_score(*values)

    def test_risk_level_boundaries_and_configurable_demo_thresholds(self):
        self.assertEqual(risk_level(1), "Niedrig")
        self.assertEqual(risk_level(6), "Niedrig")
        self.assertEqual(risk_level(7), "Mittel")
        self.assertEqual(risk_level(14), "Mittel")
        self.assertEqual(risk_level(15), "Hoch")
        self.assertEqual(risk_level(25), "Hoch")
        custom = RiskThresholds(low_max=4, medium_max=10)
        self.assertEqual(risk_level(4, custom), "Niedrig")
        self.assertEqual(risk_level(5, custom), "Mittel")
        self.assertEqual(risk_level(11, custom), "Hoch")
        for invalid_score in (0, 26, True, 4.5):
            with self.subTest(score=invalid_score), self.assertRaises(RiskInputError):
                risk_level(invalid_score)

    def test_thresholds_load_from_environment_and_reject_invalid_order(self):
        with patch.dict(os.environ, {
            "RISKRADAR_LOW_MAX_SCORE": "5",
            "RISKRADAR_MEDIUM_MAX_SCORE": "12",
        }):
            self.assertEqual(RiskThresholds.from_environment(), RiskThresholds(5, 12))
        with self.assertRaises(RiskInputError):
            RiskThresholds(low_max=14, medium_max=6)
        with patch.dict(os.environ, {"RISKRADAR_LOW_MAX_SCORE": "invalid"}):
            with self.assertRaises(RiskInputError):
                RiskThresholds.from_environment()

    def test_matrix_groups_collisions_and_rejects_malformed_values(self):
        risks = [
            {"title": "Risiko A", "probability": 4, "impact": 3},
            {"title": "Risiko B", "probability": 4, "impact": 3},
            {"title": "Risiko C", "probability": 2, "impact": 5},
        ]
        cells = group_risks_by_cell(risks)
        self.assertEqual([risk["title"] for risk in cells[(4, 3)]], ["Risiko A", "Risiko B"])
        self.assertEqual(len(cells[(2, 5)]), 1)
        for malformed in ([{"probability": 0, "impact": 3}], [{"probability": "2", "impact": 3}], [{}]):
            with self.subTest(malformed=malformed), self.assertRaises((RiskInputError, KeyError)):
                group_risks_by_cell(malformed)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(dir=PROJECT_ROOT)
        self.db_path = Path(self.tempdir.name) / "test.db"
        initialize_db(self.db_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_initialize_is_repeatable(self):
        initialize_db(self.db_path)
        initialize_db(self.db_path)
        self.assertEqual(list_projects(self.db_path), [])

    def test_initialize_upgrades_legacy_schema_without_losing_rows(self):
        legacy_path = Path(self.tempdir.name) / "legacy.db"
        with sqlite3.connect(legacy_path) as connection:
            connection.executescript(
                """CREATE TABLE projects (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL UNIQUE,
                       description TEXT NOT NULL DEFAULT '',
                       created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                   );
                   CREATE TABLE risks (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                       title TEXT NOT NULL,
                       description TEXT NOT NULL DEFAULT '',
                       probability INTEGER NOT NULL CHECK(probability BETWEEN 1 AND 5),
                       impact INTEGER NOT NULL CHECK(impact BETWEEN 1 AND 5),
                       created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                   );
                   INSERT INTO projects (name) VALUES ('Legacy-Projekt');
                   INSERT INTO risks (project_id, title, probability, impact)
                       VALUES (1, 'Legacy-Risiko', 2, 4);"""
            )
        initialize_db(legacy_path)
        self.assertEqual([project["name"] for project in list_projects(legacy_path)], ["Legacy-Projekt"])
        self.assertEqual([risk["title"] for risk in list_risks(db_path=legacy_path)], ["Legacy-Risiko"])

    def test_initialize_preserves_case_only_duplicates_and_rejects_new_duplicates(self):
        legacy_path = Path(self.tempdir.name) / "case-duplicates.db"
        with sqlite3.connect(legacy_path) as connection:
            connection.executescript(
                """CREATE TABLE projects (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL UNIQUE,
                       description TEXT NOT NULL DEFAULT '',
                       created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                   );
                   CREATE TABLE risks (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                       title TEXT NOT NULL,
                       description TEXT NOT NULL DEFAULT '',
                       probability INTEGER NOT NULL CHECK(probability BETWEEN 1 AND 5),
                       impact INTEGER NOT NULL CHECK(impact BETWEEN 1 AND 5),
                       created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                   );
                   INSERT INTO projects (name) VALUES
                       ('Legacy Alpha'), ('legacy alpha'), ('Straße'), ('STRASSE');
                   INSERT INTO risks (project_id, title, probability, impact)
                       VALUES (1, 'Legacy Risk', 2, 4), (1, 'legacy risk', 3, 3),
                              (2, 'Straße', 2, 3), (2, 'STRASSE', 3, 2);"""
            )

        initialize_db(legacy_path)
        initialize_db(legacy_path)
        projects = list_projects(legacy_path)
        risks = list_risks(db_path=legacy_path)
        self.assertEqual(len(projects), 4)
        self.assertEqual(len(risks), 4)
        self.assertEqual({project["name"].casefold() for project in projects}, {"legacy alpha", "strasse"})
        self.assertEqual({risk["title"].casefold() for risk in risks}, {"legacy risk", "strasse"})

        with self.assertRaises(DuplicateRecordError):
            add_project("LEGACY ALPHA", "", legacy_path)
        with self.assertRaises(DuplicateRecordError):
            add_risk(1, "LEGACY RISK", "", 1, 1, legacy_path)
        with self.assertRaises(DuplicateRecordError):
            add_project("StraSSe", "", legacy_path)
        with self.assertRaises(DuplicateRecordError):
            add_risk(2, "STRASSE", "", 1, 1, legacy_path)

        new_project_id = add_project("Neues Vorhaben", "", legacy_path)
        add_risk(new_project_id, "Neues Risiko", "", 1, 1, legacy_path)
        self.assertEqual(len(list_projects(legacy_path)), 5)

    def test_project_and_risk_round_trip_and_rating_boundaries(self):
        project_id = add_project(" Testprojekt ", " Beschreibung ", self.db_path)
        add_risk(project_id, "Testgefahr", "Details", 1, 5, self.db_path)
        self.assertEqual(list_projects(self.db_path)[0]["name"], "Testprojekt")
        risk = list_risks(db_path=self.db_path)[0]
        self.assertEqual((risk["title"], risk["probability"], risk["impact"]), ("Testgefahr", 1, 5))

    def test_project_input_validation(self):
        for args in (("  ", ""), ("x" * 201, ""), (None, ""), ("Valid", None)):
            with self.subTest(args=args), self.assertRaises(DataValidationError):
                add_project(*args, db_path=self.db_path)
        self.assertEqual(add_project("Projekt", "", self.db_path) > 0, True)

    def test_risk_validation_including_invalid_project_ids(self):
        project_id = add_project("Projekt", "", self.db_path)
        for probability, impact in ((0, 3), (6, 3), (3, 0), (3, 6), (True, 3), (2.5, 2)):
            with self.subTest(probability=probability, impact=impact), self.assertRaises(DataValidationError):
                add_risk(project_id, "Titel", "", probability, impact, self.db_path)
        for invalid_id in (0, -1, True, "1", 999):
            with self.subTest(project_id=invalid_id), self.assertRaises(DataValidationError):
                add_risk(invalid_id, "Titel", "", 1, 1, self.db_path)
        for title in ("", " " * 2, "x" * 201):
            with self.subTest(title=title), self.assertRaises(DataValidationError):
                add_risk(project_id, title, "", 1, 1, self.db_path)

    def test_duplicate_project_and_risk_records_are_reported(self):
        project_id = add_project("Projekt Alpha", "", self.db_path)
        with self.assertRaises(DuplicateRecordError):
            add_project("projekt alpha", "", self.db_path)
        add_risk(project_id, "Doppeltes Risiko", "", 2, 2, self.db_path)
        with self.assertRaises(DuplicateRecordError):
            add_risk(project_id, "doppeltes risiko", "", 5, 5, self.db_path)
        self.assertEqual(len(list_risks(db_path=self.db_path)), 1)

    def test_new_unicode_casefold_duplicates_are_rejected(self):
        project_id = add_project("Straße", "", self.db_path)
        with self.assertRaises(DuplicateRecordError):
            add_project("STRASSE", "", self.db_path)
        add_risk(project_id, "Maßnahme", "", 2, 3, self.db_path)
        with self.assertRaises(DuplicateRecordError):
            add_risk(project_id, "MASSNAHME", "", 2, 3, self.db_path)

    def test_risk_listing_filters_by_project(self):
        first = add_project("Projekt A", "", self.db_path)
        second = add_project("Projekt B", "", self.db_path)
        add_risk(first, "Risiko A", "", 2, 2, self.db_path)
        add_risk(second, "Risiko B", "", 4, 4, self.db_path)
        self.assertEqual([risk["title"] for risk in list_risks(first, self.db_path)], ["Risiko A"])
        with self.assertRaises(DataValidationError):
            list_risks(0, self.db_path)

    def test_seed_is_idempotent_and_leaves_nonempty_database_untouched(self):
        seed_sample_data(self.db_path)
        seed_sample_data(self.db_path)
        self.assertEqual(len(list_projects(self.db_path)), 5)
        self.assertEqual(len(list_risks(db_path=self.db_path)), 10)
        add_project("Eigenes Projekt", "", self.db_path)
        seed_sample_data(self.db_path)
        self.assertEqual(len(list_projects(self.db_path)), 6)
        self.assertEqual(len(list_risks(db_path=self.db_path)), 10)

    def test_seed_rolls_back_all_rows_on_mid_seed_failure(self):
        connection = sqlite3.connect(self.db_path)
        try:
            with connection:
                connection.execute(
                    """CREATE TRIGGER fail_sample_risk BEFORE INSERT ON risks
                       WHEN NEW.title = 'Schnittstellen nicht rechtzeitig bereit'
                       BEGIN SELECT RAISE(ABORT, 'injected seed failure'); END"""
                )
        finally:
            connection.close()
        with self.assertRaises(DatabaseOperationError):
            seed_sample_data(self.db_path)
        self.assertEqual(list_projects(self.db_path), [])
        self.assertEqual(list_risks(db_path=self.db_path), [])

    def test_database_errors_are_translated_without_catching_other_exceptions(self):
        missing_parent = Path(self.tempdir.name) / "missing" / "bad.db"
        with self.assertRaises(DatabaseOperationError):
            list_projects(missing_parent)
        with self.assertRaises(DataValidationError):
            list_projects("")

    def test_connections_are_closed_after_successful_reads(self):
        opened = []
        original_get_connection = riskradar_db.get_connection

        def tracking_connection(path):
            connection = original_get_connection(path)
            opened.append(connection)
            return connection

        with patch.object(riskradar_db, "get_connection", side_effect=tracking_connection):
            list_projects(self.db_path)
        self.assertEqual(len(opened), 1)
        with self.assertRaises(sqlite3.ProgrammingError):
            opened[0].execute("SELECT 1")

    def test_connections_are_closed_after_database_errors(self):
        add_project("Einmalig", "", self.db_path)
        opened = []
        original_get_connection = riskradar_db.get_connection

        def tracking_connection(path):
            connection = original_get_connection(path)
            opened.append(connection)
            return connection

        with patch.object(riskradar_db, "get_connection", side_effect=tracking_connection):
            with self.assertRaises(DuplicateRecordError):
                add_project("Einmalig", "", self.db_path)
        self.assertEqual(len(opened), 1)
        with self.assertRaises(sqlite3.ProgrammingError):
            opened[0].execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()

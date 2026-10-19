import tempfile
import unittest
from pathlib import Path

from risk_logic import calculate_score, group_risks_by_cell, risk_level
from riskradar_db import add_project, add_risk, initialize_db, list_projects, list_risks, seed_sample_data


class RiskLogicTests(unittest.TestCase):
    def test_score_is_probability_times_impact(self):
        self.assertEqual(calculate_score(4, 5), 20)

    def test_score_rejects_out_of_range_values(self):
        for values in ((0, 2), (6, 2), (3, 0), (3, 6)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                calculate_score(*values)

    def test_risk_levels(self):
        self.assertEqual(risk_level(6), "Niedrig")
        self.assertEqual(risk_level(8), "Mittel")
        self.assertEqual(risk_level(15), "Hoch")

    def test_matrix_keeps_multiple_risks_in_the_same_cell(self):
        risks = [
            {"title": "Risiko A", "probability": 4, "impact": 3},
            {"title": "Risiko B", "probability": 4, "impact": 3},
            {"title": "Risiko C", "probability": 2, "impact": 5},
        ]
        cells = group_risks_by_cell(risks)
        self.assertEqual([risk["title"] for risk in cells[(4, 3)]], ["Risiko A", "Risiko B"])
        self.assertEqual(len(cells[(2, 5)]), 1)

    def test_matrix_rejects_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            group_risks_by_cell([{"probability": 0, "impact": 3}])


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "test.db"
        initialize_db(self.db_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_project_and_risk_round_trip(self):
        project_id = add_project("Testprojekt", "Beschreibung", self.db_path)
        add_risk(project_id, "Testgefahr", "Details", 4, 3, self.db_path)
        self.assertEqual(len(list_projects(self.db_path)), 1)
        risk = list_risks(db_path=self.db_path)[0]
        self.assertEqual((risk["title"], risk["probability"], risk["impact"]), ("Testgefahr", 4, 3))

    def test_sample_seed_creates_five_projects_and_is_idempotent(self):
        seed_sample_data(self.db_path)
        seed_sample_data(self.db_path)
        self.assertEqual(len(list_projects(self.db_path)), 5)
        self.assertEqual(len(list_risks(db_path=self.db_path)), 10)

    def test_database_rejects_invalid_rating(self):
        project_id = add_project("Projekt", "", self.db_path)
        with self.assertRaises(Exception):
            add_risk(project_id, "Ungültig", "", 0, 3, self.db_path)

    def test_risk_listing_can_be_filtered_by_project(self):
        first_project = add_project("Projekt A", "", self.db_path)
        second_project = add_project("Projekt B", "", self.db_path)
        add_risk(first_project, "Risiko A", "", 2, 2, self.db_path)
        add_risk(second_project, "Risiko B", "", 4, 4, self.db_path)
        filtered = list_risks(first_project, self.db_path)
        self.assertEqual([risk["title"] for risk in filtered], ["Risiko A"])


if __name__ == "__main__":
    unittest.main()

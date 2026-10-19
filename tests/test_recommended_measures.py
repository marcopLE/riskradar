"""Coverage for the deterministic recommended-measures catalog."""

import unittest

from risk_logic import RiskThresholds
from recommended_measures import (
    FALLBACK_CATEGORY,
    FALLBACK_MEASURES,
    RULES,
    recommend_measures,
)


class RecommendedMeasuresTests(unittest.TestCase):
    def test_each_catalog_category_matches_and_has_two_to_four_suggestions(self):
        examples = {
            "Projektverzögerung": "Meilenstein droht sich zu verzögern",
            "Budgetüberschreitung": "Budget könnte überschritten werden",
            "Personalausfall": "Ausfall einer Schlüsselperson",
            "Anforderungsänderungen": "Anforderungsänderung nach Freigabe",
            "Sicherheitsrisiken": "Fehlkonfiguration von Zugriffsrechten",
            "Technische Probleme": "Technische Schnittstelle instabil",
            "Lieferantenabhängigkeit": "Lieferant verschiebt die Lieferung",
            "Qualitätsprobleme": "Qualitätsmangel bei der Abnahme",
        }
        self.assertEqual(set(examples), {rule.category for rule in RULES})
        for index, (category, title) in enumerate(examples.items(), start=1):
            with self.subTest(category=category):
                plan, = recommend_measures([{
                    "id": index,
                    "title": title,
                    "description": "Fiktive Beschreibung.",
                    "probability": 3,
                    "impact": 4,
                }])
                self.assertEqual(plan.category, category)
                self.assertGreaterEqual(len(plan.measures), 2)
                self.assertLessEqual(len(plan.measures), 4)
                self.assertEqual(len(set(plan.measures)), len(plan.measures))

    def test_unknown_risk_receives_explicit_generic_fallback(self):
        plan, = recommend_measures([{
            "id": 1,
            "title": "Ungewöhnliches Projektrisiko",
            "description": "Fiktiver Sachverhalt ohne Katalogbegriffe.",
            "probability": 1,
            "impact": 1,
        }])
        self.assertEqual(plan.category, FALLBACK_CATEGORY)
        self.assertIn("Fallback", plan.category)
        self.assertEqual(plan.measures, FALLBACK_MEASURES)
        self.assertGreaterEqual(len(plan.measures), 2)
        self.assertLessEqual(len(plan.measures), 4)

    def test_similar_words_do_not_trigger_wrong_categories(self):
        cases = (
            ("Unsicherheit bei der Projektfinanzierung", "Budgetüberschreitung"),
            ("Sicherstellung der Projektfinanzierung", "Budgetüberschreitung"),
            ("Zugang zum Zielmarkt verzögert sich", "Projektverzögerung"),
            ("Sicherheit des Liefertermins nicht gegeben", "Projektverzögerung"),
            ("Personalkosten steigen", "Budgetüberschreitung"),
            ("Sicherheitsrisiko im Portal", "Sicherheitsrisiken"),
            ("Sicherheitsvorfall untersuchen", "Sicherheitsrisiken"),
            ("IT-Sicherheit gefährdet", "Sicherheitsrisiken"),
            ("Sicherheit der Kundendaten gefährdet", "Sicherheitsrisiken"),
            ("Unbefugter Zugriff auf Projektdaten", "Sicherheitsrisiken"),
            ("Zu breite Berechtigungen", "Sicherheitsrisiken"),
            ("Personalausfall im Projektteam", "Personalausfall"),
            ("Schlüsselperson ist nicht verfügbar", "Personalausfall"),
        )
        for index, (title, expected_category) in enumerate(cases, start=1):
            with self.subTest(title=title):
                plan, = recommend_measures([{
                    "id": index,
                    "title": title,
                    "description": "Fiktive Beschreibung.",
                    "probability": 3,
                    "impact": 3,
                }])
                self.assertEqual(plan.category, expected_category)

    def test_first_matching_catalog_rule_wins_for_mixed_text(self):
        plan, = recommend_measures([{
            "id": 1,
            "title": "Sicherheitsvorfall mit Personalkosten",
            "description": "Fiktiver gemischter Sachverhalt.",
            "probability": 3,
            "impact": 3,
        }])
        self.assertEqual(plan.category, "Sicherheitsrisiken")

    def test_non_text_title_and_description_safely_use_fallback(self):
        plan, = recommend_measures([{
            "id": 1,
            "title": None,
            "description": object(),
            "probability": 2,
            "impact": 2,
        }])
        self.assertEqual(plan.category, FALLBACK_CATEGORY)

    def test_priority_boundaries_use_configured_thresholds_and_sort_order(self):
        thresholds = RiskThresholds(low_max=5, medium_max=12)
        risks = [
            {"id": 1, "title": "Niedrig", "description": "", "probability": 1, "impact": 5},
            {"id": 2, "title": "Mittel", "description": "", "probability": 3, "impact": 2},
            {"id": 3, "title": "Mittel obere Grenze", "description": "", "probability": 3, "impact": 4},
            {"id": 4, "title": "Hoch", "description": "", "probability": 3, "impact": 5},
            {"id": 5, "title": "Niedrig obere Grenze", "description": "", "probability": 1, "impact": 5},
        ]
        plans = recommend_measures(risks, thresholds)
        priorities = {plan.risk_id: plan.priority for plan in plans}
        self.assertEqual(priorities, {
            1: "Niedrig", 2: "Mittel", 3: "Mittel", 4: "Hoch", 5: "Niedrig",
        })
        self.assertEqual([plan.score for plan in plans], [15, 12, 6, 5, 5])


if __name__ == "__main__":
    unittest.main()

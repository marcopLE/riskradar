"""Rule-based, non-binding mitigation suggestions for project risks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from risk_logic import (
    DEFAULT_RISK_THRESHOLDS,
    RiskThresholds,
    calculate_score,
    risk_level,
)


@dataclass(frozen=True)
class MeasureRule:
    category: str
    keywords: tuple[str, ...]
    measures: tuple[str, ...]


@dataclass(frozen=True)
class RiskMeasurePlan:
    risk_id: int
    title: str
    project_name: str
    score: int
    priority: str
    category: str
    measures: tuple[str, ...]


RULES: tuple[MeasureRule, ...] = (
    MeasureRule("Sicherheitsrisiken", (
        "sicherheits", "it-sicherheit", "sicherheit der kunden", "sicherheit der daten",
        "security", "zugriff", "berechtig", "authent",
        "datenschutz", "datenleck", "verschlüssel", "cyber", "phishing", "ransom",
    ), (
        "Betroffene Zugriffe und Datenflüsse mit dem Sicherheitsteam prüfen.",
        "Eine gezielte Sicherheitsprüfung mit dokumentierten Befunden einplanen.",
        "Eskalationsweg und erste Reaktionsschritte für einen Sicherheitsvorfall festlegen.",
    )),
    MeasureRule("Lieferantenabhängigkeit", (
        "lieferant", "lieferung", "zuliefer", "dienstleister", "anbieter", "provider",
        "supplier", "extern",
    ), (
        "Liefergegenstände, Abnahmekriterien und Verantwortliche schriftlich abstimmen.",
        "Liefertermine mit regelmäßigen Statuspunkten und Vorwarnfristen verfolgen.",
        "Eine Ausweichoption oder einen internen Übergangsplan bewerten.",
    )),
    MeasureRule("Anforderungsänderungen", (
        "anforder", "änderung", "scope", "change request", "fachkonzept", "lastenheft",
    ), (
        "Änderungen vor Umsetzung auf Termin-, Kosten- und Qualitätswirkung bewerten.",
        "Eine freigegebene Anforderungsbaseline und einen Änderungsweg festhalten.",
        "Offene Änderungswünsche priorisieren und nicht freigegebene Punkte sichtbar halten.",
    )),
    MeasureRule("Personalausfall", (
        "personalausfall", "personalengpass", "personalmangel", "personal fällt aus",
        "personal fehlt", "mitarbeit", "abwesen", "krank", "schlüsselperson", "staff", "absence",
    ), (
        "Kritisches Wissen dokumentieren und mindestens eine Vertretung einarbeiten.",
        "Kapazitätsplanung und Abhängigkeiten von Schlüsselpersonen regelmäßig prüfen.",
        "Für kurzfristige Ausfälle Aufgaben priorisieren und Vertretungen benennen.",
    )),
    MeasureRule("Budgetüberschreitung", (
        "budget", "personalkosten", "projektfinanz", "kosten", "finanz", "preissteiger",
        "kostenüberschreit",
    ), (
        "Restaufwand und Prognose regelmäßig mit dem genehmigten Budget abgleichen.",
        "Kostenabweichungen nach Ursache aufschlüsseln und Gegenmaßnahmen festlegen.",
        "Reservebedarf und Eskalationsgrenze mit der Projektleitung abstimmen.",
    )),
    MeasureRule("Projektverzögerung", (
        "verzöger", "verspät", "liefertermin", "termin", "zeitplan", "meilenstein",
        "frist", "projektverzug",
    ), (
        "Kritischen Pfad und abhängige Arbeitspakete gemeinsam aktualisieren.",
        "Meilensteinprognosen engmaschig prüfen und Abweichungen früh eskalieren.",
        "Puffer und mögliche Umpriorisierungen für terminrelevante Aufgaben bewerten.",
    )),
    MeasureRule("Qualitätsprobleme", (
        "qualität", "test", "abnahme", "mangel", "defekt", "barrierefrei", "testabdeckung",
    ), (
        "Abnahmekriterien mit den betroffenen Fachbereichen konkretisieren.",
        "Testabdeckung für die betroffenen Abläufe erhöhen und Ergebnisse nachvollziehbar halten.",
        "Mängel nach Auswirkung priorisieren und vor der Abnahme erneut prüfen.",
    )),
    MeasureRule("Technische Probleme", (
        "schnittstell", "api", "server", "system", "migration", "kompat", "techn",
        "ausfall", "performance", "datenbank", "infrastruktur", "fehler",
    ), (
        "Ein technisches Prüfszenario oder einen begrenzten Prototyp für die kritische Annahme erstellen.",
        "Monitoring und klare Warnschwellen für die betroffene Komponente festlegen.",
        "Rückfall- oder Wiederherstellungsschritte vor der Änderung testen.",
    )),
)

FALLBACK_CATEGORY = "Allgemeines Risiko (Fallback)"
FALLBACK_MEASURES = (
    "Ursache, mögliche Auswirkung und frühe Warnsignale mit dem Projektteam konkretisieren.",
    "Eine verantwortliche Person und einen nächsten Prüftermin festlegen.",
    "Gegenmaßnahme, Eskalationsauslöser und Vorgehen bei Eintritt dokumentieren.",
)


def _matching_rule(risk: dict[str, Any]) -> MeasureRule | None:
    text_fields = (risk.get("title"), risk.get("description"))
    search_text = " ".join(value for value in text_fields if isinstance(value, str)).casefold()
    for rule in RULES:
        if any(re.search(rf"(?<!\w){re.escape(keyword)}", search_text) for keyword in rule.keywords):
            return rule
    return None


def recommend_measures(
    risks: Iterable[dict[str, Any]],
    thresholds: RiskThresholds = DEFAULT_RISK_THRESHOLDS,
) -> list[RiskMeasurePlan]:
    """Return one categorized plan per risk, ordered by priority then score."""
    plans: list[RiskMeasurePlan] = []
    for risk in risks:
        score = calculate_score(risk["probability"], risk["impact"])
        rule = _matching_rule(risk)
        title = risk.get("title")
        project_name = risk.get("project_name", "")
        plans.append(RiskMeasurePlan(
            risk_id=risk["id"],
            title=title if isinstance(title, str) else "",
            project_name=project_name if isinstance(project_name, str) else "",
            score=score,
            priority=risk_level(score, thresholds),
            category=rule.category if rule else FALLBACK_CATEGORY,
            measures=rule.measures if rule else FALLBACK_MEASURES,
        ))

    priority_order = {"Hoch": 0, "Mittel": 1, "Niedrig": 2}
    return sorted(plans, key=lambda plan: (priority_order[plan.priority], -plan.score, plan.title.casefold(), plan.risk_id))

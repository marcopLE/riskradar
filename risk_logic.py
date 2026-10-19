"""Pure risk scoring helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable


class RiskInputError(ValueError):
    """Raised when risk values or risk model configuration are invalid."""


@dataclass(frozen=True)
class RiskThresholds:
    """Demonstration thresholds; they are configurable but not domain-validated."""

    low_max: int = 6
    medium_max: int = 14

    def __post_init__(self) -> None:
        if (type(self.low_max) is not int or type(self.medium_max) is not int
                or not 1 <= self.low_max < self.medium_max <= 25):
            raise RiskInputError("Schwellen müssen ganze Zahlen mit 1 <= niedrig < mittel <= 25 sein.")

    @classmethod
    def from_environment(cls) -> RiskThresholds:
        try:
            low_max = int(os.environ.get("RISKRADAR_LOW_MAX_SCORE", "6"))
            medium_max = int(os.environ.get("RISKRADAR_MEDIUM_MAX_SCORE", "14"))
        except ValueError as exc:
            raise RiskInputError("Risikoschwellen in der Umgebungskonfiguration müssen ganze Zahlen sein.") from exc
        return cls(low_max=low_max, medium_max=medium_max)


DEFAULT_RISK_THRESHOLDS = RiskThresholds.from_environment()


def calculate_score(probability: int, impact: int) -> int:
    if (type(probability) is not int or type(impact) is not int
            or not 1 <= probability <= 5 or not 1 <= impact <= 5):
        raise RiskInputError("Eintrittswahrscheinlichkeit und Auswirkung müssen zwischen 1 und 5 liegen.")
    return probability * impact


def risk_level(score: int, thresholds: RiskThresholds = DEFAULT_RISK_THRESHOLDS) -> str:
    if type(score) is not int or not 1 <= score <= 25:
        raise RiskInputError("Der Risikoscore muss eine ganze Zahl zwischen 1 und 25 sein.")
    if score <= thresholds.low_max:
        return "Niedrig"
    if score <= thresholds.medium_max:
        return "Mittel"
    return "Hoch"


def risk_color(score: int, thresholds: RiskThresholds = DEFAULT_RISK_THRESHOLDS) -> str:
    return {"Niedrig": "#2e8b57", "Mittel": "#d99000", "Hoch": "#c0392b"}[
        risk_level(score, thresholds)
    ]


def group_risks_by_cell(
    risks: Iterable[dict[str, Any]],
) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """Group risks by (probability, impact) without dropping cell collisions."""
    cells: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for risk in risks:
        if not isinstance(risk, dict) or "probability" not in risk or "impact" not in risk:
            raise RiskInputError("Jedes Risiko benötigt Wahrscheinlichkeit und Auswirkung.")
        probability = risk["probability"]
        impact = risk["impact"]
        calculate_score(probability, impact)
        cells.setdefault((probability, impact), []).append(risk)
    return cells

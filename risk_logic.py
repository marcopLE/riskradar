"""Pure risk scoring helpers."""


def calculate_score(probability: int, impact: int) -> int:
    if not 1 <= probability <= 5 or not 1 <= impact <= 5:
        raise ValueError("Eintrittswahrscheinlichkeit und Auswirkung müssen zwischen 1 und 5 liegen.")
    return probability * impact


def risk_level(score: int) -> str:
    if not 1 <= score <= 25:
        raise ValueError("Der Risikoscore muss zwischen 1 und 25 liegen.")
    if score <= 6:
        return "Niedrig"
    if score <= 14:
        return "Mittel"
    return "Hoch"


def risk_color(score: int) -> str:
    return {"Niedrig": "#2e8b57", "Mittel": "#d99000", "Hoch": "#c0392b"}[risk_level(score)]

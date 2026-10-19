"""SQLite persistence and sample data for RiskRadar."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).with_name("riskradar.db")


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with get_connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS risks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                probability INTEGER NOT NULL CHECK(probability BETWEEN 1 AND 5),
                impact INTEGER NOT NULL CHECK(impact BETWEEN 1 AND 5),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def add_project(name: str, description: str, db_path: str | Path = DEFAULT_DB_PATH) -> int:
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name.strip(), description.strip()),
        )
        return int(cursor.lastrowid)


def add_risk(
    project_id: int,
    title: str,
    description: str,
    probability: int,
    impact: int,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """INSERT INTO risks (project_id, title, description, probability, impact)
               VALUES (?, ?, ?, ?, ?)""",
            (project_id, title.strip(), description.strip(), probability, impact),
        )
        return int(cursor.lastrowid)


def list_projects(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT id, name, description, created_at FROM projects ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [dict(row) for row in rows]


def list_risks(project_id: int | None = None, db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    query = """SELECT r.id, r.project_id, p.name AS project_name, r.title, r.description,
                      r.probability, r.impact, r.created_at
               FROM risks r JOIN projects p ON p.id = r.project_id"""
    params: tuple[Any, ...] = ()
    if project_id is not None:
        query += " WHERE r.project_id = ?"
        params = (project_id,)
    query += " ORDER BY r.probability * r.impact DESC, r.title COLLATE NOCASE"
    with get_connection(db_path) as connection:
        rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def seed_sample_data(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Insert five illustrative projects and risks into an empty project table."""
    samples = [
        ("ERP-Migration", "Ablösung des ERP-Systems und Migration der Kerndaten.", [
            ("Datenqualität unzureichend", "Uneinheitliche Stammdaten können die Migration verzögern.", 4, 4),
            ("Schnittstellen nicht rechtzeitig bereit", "Abhängige Systeme könnten ihre APIs verspätet liefern.", 3, 4),
        ]),
        ("Cloud-Modernisierung", "Schrittweise Verlagerung ausgewählter Dienste in die Cloud.", [
            ("Kosten überschreiten Budget", "Ungeplante Lastspitzen erhöhen die laufenden Cloud-Kosten.", 3, 4),
            ("Fehlkonfiguration von Zugriffsrechten", "Zu breite Berechtigungen könnten Daten offenlegen.", 2, 5),
        ]),
        ("Kundenportal 2.0", "Neues Self-Service-Portal für Kunden und Support-Teams.", [
            ("Lasttests decken Engpass auf", "Das Portal könnte bei hoher Nachfrage langsam reagieren.", 3, 3),
            ("Barrierefreiheit nicht erfüllt", "Nacharbeiten könnten den Veröffentlichungstermin verschieben.", 2, 3),
        ]),
        ("IAM-Rollout", "Einführung eines zentralen Identity- und Access-Managements.", [
            ("Ausfall bei der Anmeldung", "Fehler beim Rollout könnten Mitarbeitende aussperren.", 2, 5),
            ("Altanwendungen nicht kompatibel", "Einige Anwendungen unterstützen den neuen Login-Standard nicht.", 3, 4),
        ]),
        ("Data-Warehouse", "Aufbau einer zentralen Analyseplattform für Unternehmensdaten.", [
            ("Datenlieferungen verspätet", "Quellsysteme stellen Daten möglicherweise nicht pünktlich bereit.", 3, 3),
            ("Datenschutzanforderungen übersehen", "Personenbezogene Daten könnten unzureichend geschützt sein.", 2, 5),
        ]),
    ]
    with get_connection(db_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        if count:
            return
        for name, description, risks in samples:
            cursor = connection.execute(
                "INSERT INTO projects (name, description) VALUES (?, ?)", (name, description)
            )
            project_id = cursor.lastrowid
            connection.executemany(
                """INSERT INTO risks (project_id, title, description, probability, impact)
                   VALUES (?, ?, ?, ?, ?)""",
                [(project_id, *risk) for risk in risks],
            )

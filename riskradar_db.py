"""Validated SQLite persistence and sample data for RiskRadar."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DEFAULT_DB_PATH = Path(__file__).with_name("riskradar.db")
MAX_NAME_LENGTH = 200
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 5000


class DatabaseError(RuntimeError):
    """Base class for expected storage failures exposed to the application."""


class DuplicateRecordError(DatabaseError):
    """Raised when a project name or per-project risk title already exists."""


class DatabaseOperationError(DatabaseError):
    """Raised when SQLite cannot complete an operation."""


class DataValidationError(ValueError):
    """Raised when persisted data is given invalid values."""


def _validate_db_path(db_path: str | Path) -> str:
    if not isinstance(db_path, (str, Path)) or not str(db_path).strip():
        raise DataValidationError("Der Datenbankpfad muss ein gültiger Pfad sein.")
    return str(db_path)


def _validate_text(value: str, field: str, maximum: int, allow_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise DataValidationError(f"{field} muss Text sein.")
    value = value.strip()
    if not allow_empty and not value:
        raise DataValidationError(f"{field} darf nicht leer sein.")
    if len(value) > maximum:
        raise DataValidationError(f"{field} darf höchstens {maximum} Zeichen enthalten.")
    return value


def _validate_project_id(project_id: int) -> int:
    if type(project_id) is not int or project_id < 1:
        raise DataValidationError("Die Projekt-ID muss eine positive ganze Zahl sein.")
    return project_id


def _validate_rating(value: int, field: str) -> int:
    if type(value) is not int or not 1 <= value <= 5:
        raise DataValidationError(f"{field} muss eine ganze Zahl zwischen 1 und 5 sein.")
    return value


def _has_casefold_duplicates(values: Iterator[tuple[Any, ...]], key_fields: tuple[int, ...]) -> bool:
    """Detect duplicates with Python Unicode casefold semantics in fetched rows."""
    seen: set[tuple[Any, ...]] = set()
    for row in values:
        key = tuple(
            row[index].casefold() if isinstance(row[index], str) else row[index]
            for index in key_fields
        )
        if key in seen:
            return True
        seen.add(key)
    return False


def _has_casefold_match(values: Iterator[str], candidate: str) -> bool:
    folded_candidate = candidate.casefold()
    return any(value.casefold() == folded_candidate for value in values)


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a configured SQLite connection; callers must close it."""
    path = _validate_db_path(db_path)
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
    except sqlite3.Error:
        if connection is not None:
            connection.close()
        raise


@contextmanager
def _connection_scope(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Commit or roll back through the connection context and always close it."""
    connection = get_connection(db_path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _database_operation(operation: str, error: sqlite3.Error) -> DatabaseOperationError:
    return DatabaseOperationError(f"Datenbankfehler beim {operation}: {error}")


def initialize_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Create or upgrade the schema atomically and safely on repeated startup."""
    try:
        with _connection_scope(db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS risks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    probability INTEGER NOT NULL CHECK(probability BETWEEN 1 AND 5),
                    impact INTEGER NOT NULL CHECK(impact BETWEEN 1 AND 5),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            # SQLite NOCASE is ASCII-only. Detect Unicode casefold collisions in
            # Python, preserving legacy rows and omitting the affected index.
            project_names = connection.execute(
                "SELECT name FROM projects ORDER BY id"
            ).fetchall()
            if not _has_casefold_duplicates(iter(tuple(row) for row in project_names), (0,)):
                connection.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_name_nocase "
                    "ON projects(name COLLATE NOCASE)"
                )
            risk_keys = connection.execute(
                "SELECT project_id, title FROM risks ORDER BY id"
            ).fetchall()
            if not _has_casefold_duplicates(iter(tuple(row) for row in risk_keys), (0, 1)):
                connection.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_risks_project_title_nocase "
                    "ON risks(project_id, title COLLATE NOCASE)"
                )
    except sqlite3.IntegrityError as exc:
        raise _database_operation("Initialisieren des Schemas", exc) from exc
    except sqlite3.Error as exc:
        raise _database_operation("Initialisieren des Schemas", exc) from exc


def add_project(name: str, description: str, db_path: str | Path = DEFAULT_DB_PATH) -> int:
    name = _validate_text(name, "Projektname", MAX_NAME_LENGTH, allow_empty=False)
    description = _validate_text(description, "Projektbeschreibung", MAX_DESCRIPTION_LENGTH)
    try:
        with _connection_scope(db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_names = connection.execute("SELECT name FROM projects").fetchall()
            if _has_casefold_match(iter(row[0] for row in existing_names), name):
                raise DuplicateRecordError("Ein Projekt mit diesem Namen existiert bereits.")
            cursor = connection.execute(
                "INSERT INTO projects (name, description) VALUES (?, ?)", (name, description)
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise DuplicateRecordError("Ein Projekt mit diesem Namen existiert bereits.") from exc
        raise _database_operation("Anlegen des Projekts", exc) from exc
    except sqlite3.Error as exc:
        raise _database_operation("Anlegen des Projekts", exc) from exc


def add_risk(
    project_id: int,
    title: str,
    description: str,
    probability: int,
    impact: int,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    project_id = _validate_project_id(project_id)
    title = _validate_text(title, "Risikotitel", MAX_TITLE_LENGTH, allow_empty=False)
    description = _validate_text(description, "Risikobeschreibung", MAX_DESCRIPTION_LENGTH)
    probability = _validate_rating(probability, "Eintrittswahrscheinlichkeit")
    impact = _validate_rating(impact, "Schadensauswirkung")
    try:
        with _connection_scope(db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_titles = connection.execute(
                "SELECT title FROM risks WHERE project_id = ?", (project_id,)
            ).fetchall()
            if _has_casefold_match(iter(row[0] for row in existing_titles), title):
                raise DuplicateRecordError("Dieses Projekt enthält bereits ein Risiko mit diesem Titel.")
            cursor = connection.execute(
                """INSERT INTO risks (project_id, title, description, probability, impact)
                   VALUES (?, ?, ?, ?, ?)""",
                (project_id, title, description, probability, impact),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        message = str(exc)
        if "UNIQUE constraint failed" in message:
            raise DuplicateRecordError("Dieses Projekt enthält bereits ein Risiko mit diesem Titel.") from exc
        if "FOREIGN KEY constraint failed" in message:
            raise DataValidationError("Das ausgewählte Projekt existiert nicht.") from exc
        if "CHECK constraint failed" in message:
            raise DataValidationError("Wahrscheinlichkeit und Auswirkung müssen jeweils 1 bis 5 sein.") from exc
        raise _database_operation("Anlegen des Risikos", exc) from exc
    except sqlite3.Error as exc:
        raise _database_operation("Anlegen des Risikos", exc) from exc


def list_projects(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    try:
        with _connection_scope(db_path) as connection:
            rows = connection.execute(
                "SELECT id, name, description, created_at FROM projects ORDER BY name COLLATE NOCASE"
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        raise _database_operation("Lesen der Projekte", exc) from exc


def list_risks(
    project_id: int | None = None, db_path: str | Path = DEFAULT_DB_PATH
) -> list[dict[str, Any]]:
    if project_id is not None:
        project_id = _validate_project_id(project_id)
    query = """SELECT r.id, r.project_id, p.name AS project_name, r.title, r.description,
                      r.probability, r.impact, r.created_at
               FROM risks r JOIN projects p ON p.id = r.project_id"""
    params: tuple[Any, ...] = ()
    if project_id is not None:
        query += " WHERE r.project_id = ?"
        params = (project_id,)
    query += " ORDER BY r.probability * r.impact DESC, r.title COLLATE NOCASE"
    try:
        with _connection_scope(db_path) as connection:
            rows = connection.execute(query, params).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        raise _database_operation("Lesen der Risiken", exc) from exc


def seed_sample_data(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Atomically seed five fictional projects once, without duplicating rows."""
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
    try:
        with _connection_scope(db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]:
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
    except sqlite3.IntegrityError as exc:
        raise _database_operation("Einfügen der Beispieldaten", exc) from exc
    except sqlite3.Error as exc:
        raise _database_operation("Einfügen der Beispieldaten", exc) from exc

# RiskRadar

RiskRadar ist eine Streamlit-Anwendung zur Verwaltung und Bewertung von Risiken in IT-Projekten. Projekte und Risiken werden lokal in SQLite gespeichert. Beim ersten Start werden fünf fiktive Projekte mit je zwei passenden Beispielsrisiken angelegt. Schemaanlage und Beispieldaten-Seeding laufen transaktionsgesichert und können wiederholt ausgeführt werden. SQLite-Verbindungen werden nach jedem Zugriff geschlossen; Eingaben werden vor dem Schreiben validiert, und Duplikate werden mit typisierten Fehlern gemeldet.

Die Risikomatrix verwendet die gespeicherten Wahrscheinlichkeits- und Auswirkungswerte als 5×5-Koordinaten. Die Geschäftslogik gruppiert Risiken je Zelle, die bestehende SQLite-Abfrage filtert nach Projekt, und Streamlit rendert die interaktive Matrix samt Zellendetails. So werden mehrere Risiken mit denselben Werten gemeinsam angezeigt, ohne Datenbank- oder Erfassungsfunktionen zu verändern.

Projektnamen und Risikotitel gelten nach Unicode-`str.casefold()` als identisch, auch wenn SQLite `NOCASE` diese Unicode-Fälle nicht erkennt. Bei einer Schemaaktualisierung bleiben vorhandene kollidierende Namen erhalten; ein betroffener eindeutiger Index wird nicht neu angelegt, damit der Start nicht scheitert und keine Altzeilen gelöscht werden. Neue Schreibvorgänge werden per Python-`casefold()` innerhalb einer SQLite-Schreibtransaktion auf Kollisionen geprüft. Falls Legacy-Projektnamen gleich aussehen, zeigen Projekt- und Matrixfilter zusätzlich die eindeutige Projekt-ID. Die Matrixlegende liest ihre Grenzwerte aus derselben Laufzeitkonfiguration wie die Risikostufen; falls die hohe Stufe keine Scores mehr umfasst, weist sie das explizit aus.

Da Streamlit Skripte im selben Python-Prozess erneut ausführt, prüft `runtime_imports.py` bei jedem Lauf, ob die erwarteten Modul-APIs vorhanden sind. Nur bei fehlenden Exporten werden die lokalen Module neu geladen; das verhindert veraltete Importzustände nach Codeänderungen.

Die Risikostufen sind ein konfigurierbares Demonstrationsmodell und fachlich nicht validiert. Standardmäßig gelten Scores bis 6 als niedrig, bis 14 als mittel und darüber als hoch. Vor dem Start lassen sie sich mit `RISKRADAR_LOW_MAX_SCORE` und `RISKRADAR_MEDIUM_MAX_SCORE` ändern; es muss `1 <= niedrig < mittel <= 25` gelten. Eine Konfiguration erfordert einen Neustart der Anwendung.

**Streamlit Community Cloud bietet keine dauerhafte Speicherung des lokalen Dateisystems.** Die dortige `riskradar.db` kann bei Neustarts oder erneutem Deployment verloren gehen. RiskRadar zeigt deshalb auch in der Oberfläche einen Hinweis darauf. Für dauerhaft gespeicherte Cloud-Daten ist eine externe persistente Datenbank erforderlich.

## Start

Voraussetzung: Python 3.10 oder neuer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Unter Windows PowerShell aktivierst du die Umgebung mit `.venv\Scripts\Activate.ps1`. Die Datenbank `riskradar.db` wird beim ersten Start im Projektordner erzeugt.

## Tests

```bash
python -m unittest discover -s tests -v
```

Die Tests verwenden `unittest` und Streamlit AppTest; installiere zuerst `requirements.txt` in der virtuellen Umgebung.

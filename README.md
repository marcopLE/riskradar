# RiskRadar

RiskRadar ist eine Streamlit-Anwendung zur Verwaltung und Bewertung von Risiken in IT-Projekten. Projekte und Risiken werden lokal in SQLite gespeichert. Beim ersten Start werden fünf fiktive Projekte mit je zwei passenden Beispielsrisiken angelegt.

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

Die Tests benötigen nur die Python-Standardbibliothek.

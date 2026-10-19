# Entwicklungsregeln für RiskRadar

Diese Regeln gelten für alle Entwicklungsarbeiten in diesem Projekt.

## Arbeitsablauf

1. **Bestand zuerst verstehen.** Lies vor jeder Änderung die betroffenen Dateien und prüfe die bestehende Architektur, Datenflüsse und vorhandenen Tests. Richte Änderungen an den bestehenden Konventionen aus.
2. **Größere Aufgaben planen.** Erstelle vor der Umsetzung größerer oder mehrere Bereiche betreffender Aufgaben einen kurzen, überprüfbaren Umsetzungsplan. Kleine, klar abgegrenzte Korrekturen können direkt umgesetzt werden.
3. **Schichten getrennt halten.** Trenne Geschäftslogik, Datenbankzugriff und Benutzeroberfläche. Die Streamlit-Oberfläche soll Berechnungen und persistente Abfragen über dafür vorgesehene Module aufrufen, statt diese Logik selbst zu implementieren.
4. **Funktionen testen.** Schreibe für jede neue Funktion automatisierte Tests, die deren erwartetes Verhalten und relevante Fehlerfälle abdecken.
5. **Gesamte Testsuite ausführen.** Führe nach jeder Änderung alle automatisierten Tests aus, nicht nur die neu hinzugefügten Tests.
6. **Fehler beheben und erneut testen.** Schlägt ein Test fehl, untersuche und behebe die Ursache eigenständig. Führe anschließend die gesamte Testsuite erneut aus und wiederhole dies, bis sie erfolgreich ist oder ein konkretes externes Hindernis verbleibt.
7. **Sicherheit und Nebenwirkungen prüfen.** Prüfe Änderungen auf Sicherheitsprobleme sowie unbeabsichtigte Auswirkungen, insbesondere bei Eingaben, Berechtigungen, Datenbankoperationen und lokalen Dateien.
8. **Architekturentscheidungen festhalten.** Dokumentiere wichtige Entscheidungen einschließlich ihres Grundes in der README oder einer passenden Projektdokumentation.
9. **Nur fiktive Testdaten verwenden.** Tests, Fixtures und Beispieldaten dürfen keine echten Personen, Organisationen, Zugangsdaten oder vertraulichen Informationen enthalten.
10. **Im Projektordner bleiben.** Lies und verändere für die Aufgabe erforderliche Dateien ausschließlich innerhalb dieses Projektordners. Erzeuge oder ändere keine Dateien außerhalb davon.

## Abschluss jeder Entwicklungsaufgabe

Berichte nach jeder Entwicklungsaufgabe knapp und vollständig:

- welche Änderungen vorgenommen wurden;
- welche Tests ausgeführt wurden und mit welchem Ergebnis;
- welche relevanten Risiken, Einschränkungen oder noch offenen Punkte verbleiben.

Erstelle keine Git-Commits und führe keine Deployments durch, solange der Nutzer diese Handlung nicht ausdrücklich freigegeben hat. Eine Freigabe für eine Entwicklungsänderung allein gilt nicht als Freigabe für Commit oder Deployment.

## Multi-Agenten-Workflow

Wenn eine Aufgabe mehrere spezialisierte Rollen erfordert und die Laufzeit Unteragenten unterstützt, koordiniert der Hauptagent die Arbeit. Für die unabhängige Prüfung werden die Rollen getrennt eingesetzt:

1. **Koordinator:** prüft Architektur und Tests, hält einen überprüfbaren Plan fest, delegiert klar abgegrenzte Arbeiten, verfolgt Findings und Korrekturschleifen und erstellt den Qualitätsbericht. Der Koordinator stellt sicher, dass alle Agenten die Regeln dieser Datei einhalten.
2. **Entwicklungsagent:** implementiert den beauftragten Umfang, ergänzt Tests, führt die gesamte Testsuite aus und meldet Änderungen sowie Ergebnisse. Er erstellt keine Commits und deployt nicht.
3. **Review-Agent:** prüft Änderungen unabhängig auf Sicherheit, Architektur, Nebenwirkungen und Testabdeckung. Er arbeitet ausschließlich lesend und verändert während der Prüfung keinen Code.

Der Review-Agent beginnt erst, wenn der Entwicklungsagent seine Änderungen und Testergebnisse gemeldet hat. Während des Reviews bearbeitet kein anderer Agent dieselben Dateien. Findings gehen anschließend an den Entwicklungsagenten zur Korrektur; danach prüft der Review-Agent die Korrekturen erneut. Der Koordinator führt zum Abschluss selbst die vereinbarte Gesamtprüfung aus und berichtet Änderungen, Testergebnisse und offene Risiken. Aufgaben dürfen zwischen Agenten übergeben werden, aber niemals so, dass Review und Codeänderung an denselben Dateien gleichzeitig stattfinden.

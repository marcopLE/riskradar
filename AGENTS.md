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

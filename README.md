# Recruiting-Dashboard

Streamlit-Dashboard mit den wichtigsten Erkenntnissen aus `applications_dataset_v2.csv`:
Bewerbungs-Funnel, fehlende Werte, Score-Verteilung, Erfolgsquote nach Fachbereich,
Discipline, Qualifikationsstatus und Anstellungsart.

**Live-App:** https://recruiting-dashboard-q5xsyhua7zszfhvfzvnpfm.streamlit.app/

## Wann hat eine Stelle "genug" Bewerbungen?

Eigene Analyse-Sektion: Für jede Stelle mit Hire wird geprüft, wie viele Interviews/Bewerbungen
bis zur mündlichen Zusage bereits stattfanden — das zeigt, ab wann eine Stelle im Rückblick
"ausreichend versorgt" war.

- Bei 56% aller Stellen mit Einstellung stand der Hire bereits nach ≤2 Interviews fest
- Craft & Construction (Handwerk & Bau) braucht im Median nur 1 Interview, Tech im Median 2 —
  und fast doppelt so viele Bewerbungen vorab (34 vs. 20)
- Bewerber-Qualität (Fit-Score, Qualifikations-Quote) erklärt den Unterschied kaum (Korrelation ~0,1) —
  der Fachbereich selbst ist der Haupttreiber, nicht die Kandidat:innen-Qualität
- Konkreter Vorschlag: Schwellenwert pro Fachbereich = Median + 1 Interview Sicherheitsmarge.
  Das hebt die Abdeckung der Hires von ~50–60% (beim reinen Median) auf ~60–78%

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Daten aktualisieren

Das Dashboard lädt keine Rohdaten, sondern kleine, vorberechnete Auswertungstabellen
aus `data/` (wegen GitHubs 100-MB-Dateilimit — die Rohdaten-CSV ist ~146 MB).

Bei neuen Rohdaten `build_data.py` erneut ausführen und die Ergebnisse committen:

```bash
python build_data.py
```

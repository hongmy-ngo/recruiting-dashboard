# Recruiting-Dashboard

Streamlit-Dashboard mit den wichtigsten Erkenntnissen aus `applications_dataset_v2.csv`:
Bewerbungs-Funnel, fehlende Werte, Score-Verteilung, Erfolgsquote nach Fachbereich,
Discipline, Qualifikationsstatus und Anstellungsart.

**Live-App:** https://recruiting-dashboard-q5xsyhua7zszfhvfzvnpfm.streamlit.app/

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

"""
Berechnet kompakte Auswertungstabellen aus applications_dataset_v2.csv
und speichert sie als kleine CSVs in data/ -- damit app.py nicht die
146-MB-Rohdatei laden/mit ins Git-Repo packen muss (GitHub-Limit 100 MB).

Ausführen (einmalig, bzw. neu wenn sich die Rohdaten ändern):
    python build_data.py
"""

import os
import pandas as pd
import numpy as np

RAW_CSV = os.path.join(os.path.dirname(__file__), "..", "recruiting-dashboard", "applications_dataset_v2.csv")
OUT_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUT_DIR, exist_ok=True)

print(f"Lade {RAW_CSV} ...")
df = pd.read_csv(RAW_CSV)
df["success"] = df["relative_date_of_acceptance"].notna()

# 1. Kennzahlen (Funnel + Grunddaten)
funnel = pd.DataFrame([
    {"schritt": "Bewerbungen", "anzahl": len(df)},
    {"schritt": "Qualifiziert", "anzahl": int(df["is_qualified_application"].sum())},
    {"schritt": "Interview", "anzahl": int(df["relative_date_of_interview"].notna().sum())},
    {"schritt": "Zusage", "anzahl": int(df["relative_date_of_assurance"].notna().sum())},
    {"schritt": "Einstellung", "anzahl": int(df["relative_date_of_acceptance"].notna().sum())},
])
funnel.to_csv(f"{OUT_DIR}/funnel.csv", index=False)

overview = pd.DataFrame([{
    "bewerbungen": len(df),
    "stellen": df["enquiry_pid"].nunique(),
    "unternehmen": df["company_pid"].nunique(),
    "kandidaten": df["candidate_pid"].nunique(),
    "erfolgsquote_pct": round(df["success"].mean() * 100, 2),
}])
overview.to_csv(f"{OUT_DIR}/overview.csv", index=False)

# 2. Fehlende Werte
missing = (df.isnull().mean() * 100).round(2).reset_index()
missing.columns = ["spalte", "fehlend_pct"]
missing = missing.sort_values("fehlend_pct", ascending=False)
missing.to_csv(f"{OUT_DIR}/missing_values.csv", index=False)

# 3. Score-Verteilung nach Erfolg (gebinnt, da overall_score in 0.1-Schritten gestuft ist)
bins = np.arange(-0.05, 1.06, 0.1)
labels = [f"{(bins[i] + bins[i+1]) / 2:.1f}" for i in range(len(bins) - 1)]
df["score_bucket"] = pd.cut(df["cjs_overall_score"], bins=bins, labels=labels)
score_dist = (
    df.dropna(subset=["score_bucket"])
    .groupby(["score_bucket", "success"], observed=True)
    .size()
    .reset_index(name="anzahl")
)
score_dist.to_csv(f"{OUT_DIR}/score_distribution.csv", index=False)

# 4. Erfolgsquote nach Fachbereich
by_area = (
    df.groupby("functional_area")
    .agg(n=("success", "count"), erfolgsquote_pct=("success", lambda x: round(x.mean() * 100, 2)))
    .reset_index()
    .sort_values("erfolgsquote_pct", ascending=False)
)
by_area.to_csv(f"{OUT_DIR}/success_by_area.csv", index=False)

# 5. Erfolgsquote nach Discipline (nur Top 20 nach Fallzahl, sonst zu klein/verrauscht)
by_discipline = (
    df.groupby("discipline")
    .agg(n=("success", "count"), erfolgsquote_pct=("success", lambda x: round(x.mean() * 100, 2)))
    .reset_index()
    .sort_values("n", ascending=False)
    .head(20)
    .sort_values("erfolgsquote_pct", ascending=False)
)
by_discipline.to_csv(f"{OUT_DIR}/success_by_discipline.csv", index=False)

# 6. Qualifiziert vs. nicht qualifiziert
by_qualified = (
    df.groupby("is_qualified_application")
    .agg(n=("success", "count"), erfolgsquote_pct=("success", lambda x: round(x.mean() * 100, 2)))
    .reset_index()
)
by_qualified.to_csv(f"{OUT_DIR}/success_by_qualified.csv", index=False)

# 7. Anstellungsart (enquiry_type_categorized)
by_type = (
    df.groupby("enquiry_type_categorized")
    .agg(n=("success", "count"), erfolgsquote_pct=("success", lambda x: round(x.mean() * 100, 2)))
    .reset_index()
)
by_type.to_csv(f"{OUT_DIR}/success_by_type.csv", index=False)

# 8. "Wie viele Bewerbungen/Interviews braucht eine Stelle wirklich?"
# Fuer jeden Job mit Hire: Zeitpunkt der muendlichen Zusage (assurance) des
# erfolgreichen Kandidaten = Moment, an dem der Hire "gesichert" war.
# Dann zaehlen wir, wie viele Interviews/Bewerbungen (ueber ALLE Kandidat:innen
# der Stelle) bis zu diesem Zeitpunkt bereits stattgefunden hatten.
hires = df[df["relative_date_of_assurance"].notna() & df["success"]].groupby("enquiry_pid")["relative_date_of_assurance"].min()
hires.name = "hire_secured_day"

apps = df[["enquiry_pid", "relative_date_of_selection", "relative_date_of_interview", "functional_area",
           "discipline", "cjs_overall_score", "is_qualified_application"]].copy()
apps = apps.merge(hires, on="enquiry_pid", how="inner")
apps["app_before_hire"] = apps["relative_date_of_selection"] <= apps["hire_secured_day"]
apps["interview_before_hire"] = apps["relative_date_of_interview"].notna() & (apps["relative_date_of_interview"] <= apps["hire_secured_day"])

per_job = apps.groupby("enquiry_pid").agg(
    functional_area=("functional_area", "first"),
    discipline=("discipline", "first"),
    n_apps_bis_hire=("app_before_hire", "sum"),
    n_interviews_bis_hire=("interview_before_hire", "sum"),
).reset_index()

pool = df.groupby("enquiry_pid").agg(
    avg_score=("cjs_overall_score", "mean"),
    qualifiziert_pct=("is_qualified_application", lambda x: round(x.mean() * 100, 1)),
).reset_index()
per_job = per_job.merge(pool, on="enquiry_pid", how="left")

# 8a. Kumulative Verteilung (gesamt + Tech + Craft & Construction zum Vergleich)
def cum_dist(sub, max_x=6):
    total = len(sub)
    rows = []
    for x in range(0, max_x + 1):
        rows.append({"interviews": x, "anteil_pct": round((sub["n_interviews_bis_hire"] <= x).mean() * 100, 1)})
    return pd.DataFrame(rows)

cum_overall = cum_dist(per_job).assign(gruppe="Alle Fachbereiche")
cum_tech = cum_dist(per_job[per_job["functional_area"] == "Tech"]).assign(gruppe="Tech")
cum_craft = cum_dist(per_job[per_job["functional_area"] == "Craft & Construction"]).assign(gruppe="Craft & Construction")
cum_all = pd.concat([cum_overall, cum_tech, cum_craft], ignore_index=True)
cum_all.to_csv(f"{OUT_DIR}/interviews_bis_hire_kumulativ.csv", index=False)

# 8b. Tabelle je Fachbereich (nur mit genug Hires fuer verlaessliche Zahlen)
area_table = per_job.groupby("functional_area").agg(
    n_hires=("enquiry_pid", "count"),
    median_interviews=("n_interviews_bis_hire", "median"),
    median_apps=("n_apps_bis_hire", "median"),
    avg_score=("avg_score", lambda x: round(x.mean(), 2)),
    qualifiziert_pct=("qualifiziert_pct", lambda x: round(x.mean(), 1)),
).reset_index()
area_table = area_table[area_table["n_hires"] >= 20].sort_values("median_interviews")

# Konkreter Schwellenwert-Vorschlag: Median + 1 Interview Sicherheitsmarge.
# Zeigt, wie viel % der Hires beim Median (~50%) vs. beim Schwellenwert
# tatsaechlich schon abgedeckt sind.
def _coverage(area, x):
    sub = per_job[per_job["functional_area"] == area]
    return round((sub["n_interviews_bis_hire"] <= x).mean() * 100, 1)

area_table["empf_schwellenwert"] = area_table["median_interviews"] + 1
area_table["abdeckung_bei_median_pct"] = area_table.apply(lambda r: _coverage(r["functional_area"], r["median_interviews"]), axis=1)
area_table["abdeckung_bei_schwellenwert_pct"] = area_table.apply(lambda r: _coverage(r["functional_area"], r["empf_schwellenwert"]), axis=1)

area_table.to_csv(f"{OUT_DIR}/interviews_bis_hire_je_fachbereich.csv", index=False)

# 8c. Interview-Schwellenwert je Discipline (gleiche Logik wie 8b, aber feiner --
# siehe Analyse im Dashboard-Chat: Discipline ist auch bei Interviews der staerkere
# Treiber als Fachbereich).
def _coverage_disc(discipline, x):
    sub = per_job[per_job["discipline"] == discipline]
    return round((sub["n_interviews_bis_hire"] <= x).mean() * 100, 1)

disc_interviews = per_job.groupby("discipline").agg(
    functional_area=("functional_area", lambda x: x.mode().iat[0]),
    n_hires=("enquiry_pid", "count"),
    median_interviews=("n_interviews_bis_hire", "median"),
).reset_index()
disc_interviews = disc_interviews[disc_interviews["n_hires"] >= 15].sort_values("median_interviews")
disc_interviews["empf_schwellenwert"] = disc_interviews["median_interviews"] + 1
disc_interviews["abdeckung_bei_median_pct"] = disc_interviews.apply(
    lambda r: _coverage_disc(r["discipline"], r["median_interviews"]), axis=1)
disc_interviews["abdeckung_bei_schwellenwert_pct"] = disc_interviews.apply(
    lambda r: _coverage_disc(r["discipline"], r["empf_schwellenwert"]), axis=1)
disc_interviews.to_csv(f"{OUT_DIR}/interviews_bis_hire_je_discipline.csv", index=False)

# 8d. Bewerbungs-Schwellenwert je Discipline (feiner als Fachbereich, siehe Analyse
# im Dashboard-Chat: Discipline ist der staerkste Treiber, nicht Bewerberqualitaet).
# Median*1.5 als Sicherheitsmarge -- reiner Median deckt konstant nur ~50% der Hires
# ab, +50% bringt ueber fast alle Disciplines hinweg auf ~60-80%.
def _coverage_apps(sub_disc, x):
    return round((sub_disc["n_apps_bis_hire"] <= x).mean() * 100, 1)

disc_table = per_job.groupby("discipline").agg(
    functional_area=("functional_area", lambda x: x.mode().iat[0]),
    n_hires=("enquiry_pid", "count"),
    median_apps=("n_apps_bis_hire", "median"),
).reset_index()
disc_table = disc_table[disc_table["n_hires"] >= 15].sort_values("median_apps")
disc_table["empf_schwellenwert"] = (disc_table["median_apps"] * 1.5).round().astype(int)
disc_table["abdeckung_bei_median_pct"] = disc_table.apply(
    lambda r: _coverage_apps(per_job[per_job["discipline"] == r["discipline"]], r["median_apps"]), axis=1)
disc_table["abdeckung_bei_schwellenwert_pct"] = disc_table.apply(
    lambda r: _coverage_apps(per_job[per_job["discipline"] == r["discipline"]], r["empf_schwellenwert"]), axis=1)

# Wie lange dauert es kalendarisch, bis der Schwellenwert an Bewerbungen erreicht ist?
# Start = erste Bewerbung der Stelle, Ziel = n-te Bewerbung (n = Schwellenwert). Nicht
# jede Stelle bekommt ueberhaupt so viele Bewerbungen -- daher zusaetzlich der Anteil,
# der den Schwellenwert je erreicht.
def _dauer_bis_schwellenwert(disc, n):
    sub = apps[apps["discipline"] == disc]
    def _tage(g):
        d = g["relative_date_of_selection"].dropna().sort_values().values
        return d[int(n) - 1] - d[0] if len(d) >= n else np.nan
    dauer = sub.groupby("enquiry_pid").apply(_tage, include_groups=False)
    return dauer.median(), round(dauer.notna().mean() * 100, 1)

_dauer_ergebnis = disc_table.apply(lambda r: _dauer_bis_schwellenwert(r["discipline"], r["empf_schwellenwert"]), axis=1)
disc_table["median_tage_bis_schwellenwert"] = [x[0] for x in _dauer_ergebnis]
disc_table["erreicht_schwellenwert_pct"] = [x[1] for x in _dauer_ergebnis]

disc_table.to_csv(f"{OUT_DIR}/bewerbungen_je_discipline.csv", index=False)

# 8e. Alternative Stopp-Regel: Bewerbungs-Stillstand statt fixer Bewerbungszahl.
# Idee aus dem Dashboard-Chat: Bei Disciplines mit niedriger Erreichungsquote (z. B.
# Field Sales, Tech Projektmanagement, Einkauf, Rechtsanwaelte) wird der empfohlene
# Bewerbungs-Schwellenwert oft nie erreicht. Alternative: stoppen, wenn X Tage lang
# keine neue Bewerbung eingeht -- das feuert IMMER (anders als die Bewerbungszahl-
# Regel, die bei ~30-70% der Stellen nie ausloest). Frage: bleibt die Erfassungsquote
# des Hires dabei vergleichbar? Getestet mit X=30 Tagen.
STAGNATION_TAGE = 30

def _stagnation_stop_day(dates, x):
    d = np.sort(dates)
    for i in range(len(d) - 1):
        if d[i + 1] - d[i] >= x:
            return d[i] + x
    return d[-1] + x

def _stagnation_stats(disc):
    sub = apps[apps["discipline"] == disc]
    rows = []
    for pid, g in sub.groupby("enquiry_pid"):
        dates = g["relative_date_of_selection"].dropna().values
        if len(dates) == 0:
            continue
        rows.append({
            "start": dates.min(),
            "stop": _stagnation_stop_day(dates, STAGNATION_TAGE),
            "hire": g["hire_secured_day"].iloc[0],
        })
    r = pd.DataFrame(rows)
    abdeckung = round((r["hire"] <= r["stop"]).mean() * 100, 1)
    median_tage = (r["stop"] - r["start"]).median()
    return abdeckung, median_tage

stagnation_table = disc_table[["discipline", "functional_area", "n_hires", "abdeckung_bei_schwellenwert_pct"]].copy()
stagnation_table = stagnation_table.rename(columns={"abdeckung_bei_schwellenwert_pct": "abdeckung_bewerbungszahl_regel_pct"})
_stag = stagnation_table["discipline"].apply(_stagnation_stats)
stagnation_table["abdeckung_stagnation_pct"] = [x[0] for x in _stag]
stagnation_table["median_tage_bis_stopp"] = [x[1] for x in _stag]
stagnation_table["differenz_pct"] = round(
    stagnation_table["abdeckung_stagnation_pct"] - stagnation_table["abdeckung_bewerbungszahl_regel_pct"], 1)
stagnation_table = stagnation_table.sort_values("differenz_pct")
stagnation_table.to_csv(f"{OUT_DIR}/stagnation_stopp_je_discipline.csv", index=False)

# 8f. Getestet, aber verworfen: qualifizierte statt rohe Bewerbungszahl als Ziel.
# Idee: vielleicht ist eine kleinere Zielzahl (nur qualifizierte Bewerbungen) leichter
# erreichbar. Ergebnis: nein -- verschlechtert die Erreichungsquote in praktisch allen
# Disciplines (im Schnitt -17 Prozentpunkte, 0 von 55 Disciplines verbessern sich).
# Tabelle dokumentiert das Ergebnis, ist keine Empfehlung.
total_qual = apps.groupby("enquiry_pid").agg(
    discipline=("discipline", "first"),
    n_qual_total=("is_qualified_application", "sum"),
).reset_index()

qual_rows = []
for _, row in disc_table.iterrows():
    disc = row["discipline"]
    sub = total_qual[total_qual["discipline"] == disc]
    med_q = sub["n_qual_total"].median()
    thresh_q = round(med_q * 1.5)
    reach_q = round((sub["n_qual_total"] >= thresh_q).mean() * 100, 1)
    qual_rows.append({
        "discipline": disc, "functional_area": row["functional_area"], "n_hires": row["n_hires"],
        "raw_schwellenwert": row["empf_schwellenwert"], "raw_erreicht_pct": row["erreicht_schwellenwert_pct"],
        "qualifiziert_schwellenwert": thresh_q, "qualifiziert_erreicht_pct": reach_q,
        "differenz_pct": round(reach_q - row["erreicht_schwellenwert_pct"], 1),
    })
qual_compare = pd.DataFrame(qual_rows).sort_values("differenz_pct")
qual_compare.to_csv(f"{OUT_DIR}/qualifiziert_vs_roh_je_discipline.csv", index=False)

print(f"Fertig. Dateien liegen in {OUT_DIR}")

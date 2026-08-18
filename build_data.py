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

print(f"Fertig. Dateien liegen in {OUT_DIR}")

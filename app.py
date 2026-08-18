"""
Recruiting-Dashboard (Streamlit)
================================
Zeigt die wichtigsten Erkenntnisse aus applications_dataset_v2.csv:
Funnel, fehlende Werte, Score-Verteilung, Erfolgsquote nach Fachbereich,
Discipline, Qualifikationsstatus und Anstellungsart.

Lädt nur vorberechnete, kleine Auswertungstabellen aus data/ (siehe
build_data.py) statt der 146-MB-Rohdatei -- läuft dadurch schnell und
passt in ein GitHub-Repo (< 100-MB-Limit).

Lokal starten:
    streamlit run app.py
"""

import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

PINK = "#D91C6E"
PINK_TINT = "#F6C9DD"
INK = "#1F2430"

st.set_page_config(page_title="Recruiting-Dashboard", layout="wide")

px.defaults.template = "plotly_white"
PLOTLY_LAYOUT = dict(template="plotly_white", paper_bgcolor="white", plot_bgcolor="white")


@st.cache_data
def load(name):
    return pd.read_csv(f"{DATA_DIR}/{name}.csv")


overview = load("overview").iloc[0]
funnel = load("funnel")
missing = load("missing_values")
score_dist = load("score_distribution")
by_area = load("success_by_area")
by_discipline = load("success_by_discipline")
by_qualified = load("success_by_qualified")
by_type = load("success_by_type")
cum_interviews = load("interviews_bis_hire_kumulativ")
area_threshold = load("interviews_bis_hire_je_fachbereich")

st.title("Recruiting-Dashboard")
st.caption("Erkenntnisse aus applications_dataset_v2.csv")

# --- KPI-Kacheln ---------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Bewerbungen", f"{int(overview['bewerbungen']):,}".replace(",", "."))
c2.metric("Stellen", f"{int(overview['stellen']):,}".replace(",", "."))
c3.metric("Unternehmen", f"{int(overview['unternehmen']):,}".replace(",", "."))
c4.metric("Kandidat:innen", f"{int(overview['kandidaten']):,}".replace(",", "."))
c5.metric("Erfolgsquote", f"{overview['erfolgsquote_pct']:.2f} %")

st.divider()

# --- Funnel ---------------------------------------------------------------
st.subheader("Bewerbungs-Funnel")
st.caption(
    "Zeigt, wie viele Bewerbungen jede Phase des Prozesses erreichen — von der "
    "ersten Bewerbung bis zur tatsächlichen Einstellung. Je schmaler der Trichter "
    "nach unten wird, desto mehr Bewerbungen gehen unterwegs verloren."
)
fig_funnel = go.Figure(go.Funnel(
    y=funnel["schritt"],
    x=funnel["anzahl"],
    textinfo="value+percent initial",
    marker={"color": [INK, PINK, PINK, "#B8135D", "#C0392B"]},
))
fig_funnel.update_layout(**PLOTLY_LAYOUT, height=380, margin=dict(t=10, l=10, r=10, b=10))
st.plotly_chart(fig_funnel, use_container_width=True)

st.divider()

col_left, col_right = st.columns(2)

# --- Score-Verteilung -------------------------------------------------
with col_left:
    st.subheader("Score-Verteilung nach Erfolg")
    st.caption(
        "Jede:r Bewerber:in bekommt einen automatischen 'Fit Score' von 0 (schlecht "
        "passend) bis 1 (sehr gut passend). Der Chart vergleicht: Haben Kandidat:innen "
        "mit hohem Score öfter tatsächlich den Job bekommen? Wenn ja, ist der Score "
        "ein sinnvolles Frühwarn-Signal."
    )
    pivot = score_dist.pivot(index="score_bucket", columns="success", values="anzahl").fillna(0)
    pivot.columns = ["Nicht eingestellt" if not c else "Eingestellt" for c in pivot.columns]
    pivot_pct = pivot.div(pivot.sum(axis=0), axis=1) * 100
    fig_score = go.Figure()
    fig_score.add_bar(x=pivot_pct.index.astype(str), y=pivot_pct["Nicht eingestellt"],
                       name="Nicht eingestellt", marker_color=PINK_TINT)
    fig_score.add_bar(x=pivot_pct.index.astype(str), y=pivot_pct["Eingestellt"],
                       name="Eingestellt", marker_color=PINK)
    fig_score.update_layout(**PLOTLY_LAYOUT, barmode="group", yaxis_title="Anteil (%)",
                             xaxis_title="Overall Score", height=380)
    st.plotly_chart(fig_score, use_container_width=True)

# --- Fehlende Werte ---------------------------------------------------
with col_right:
    st.subheader("Fehlende Werte je Spalte")
    st.caption(
        "Nicht jede Spalte ist für jede Bewerbung befüllt — z. B. gibt es nur dann "
        "ein Interview-Datum, wenn es wirklich zu einem Interview kam. Hohe Werte "
        "hier sind meist normal (späte Prozessschritte, die nur wenige erreichen), "
        "kein Datenfehler."
    )
    fig_missing = px.bar(missing, x="fehlend_pct", y="spalte", orientation="h",
                          color_discrete_sequence=[PINK])
    fig_missing.update_layout(**PLOTLY_LAYOUT, xaxis_title="Fehlend (%)", yaxis_title="", height=380,
                               yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig_missing, use_container_width=True)

st.divider()

# --- Erfolgsquote nach Fachbereich -------------------------------------
st.subheader("Erfolgsquote nach Fachbereich")
st.caption(
    "Wie hoch ist der Anteil der Bewerbungen, die am Ende zu einer Einstellung "
    "führen — aufgeschlüsselt nach Fachbereich (z. B. Tech, Marketing, Finance)? "
    "Zeigt, in welchen Bereichen es leichter oder schwerer ist, jemanden erfolgreich "
    "einzustellen."
)
fig_area = px.bar(by_area, x="erfolgsquote_pct", y="functional_area", orientation="h",
                   hover_data=["n"], color_discrete_sequence=[PINK])
fig_area.update_layout(**PLOTLY_LAYOUT, xaxis_title="Erfolgsquote (%)", yaxis_title="", height=520,
                        yaxis=dict(categoryorder="total ascending"))
st.plotly_chart(fig_area, use_container_width=True)

col_left2, col_right2 = st.columns(2)

# --- Erfolgsquote nach Discipline (Top 20) ------------------------------
with col_left2:
    st.subheader("Erfolgsquote nach Discipline (Top 20 nach Fallzahl)")
    st.caption(
        "Gleiche Idee wie oben, nur feiner unterteilt: 'Discipline' ist die genauere "
        "Job-Kategorie innerhalb eines Fachbereichs (z. B. 'Software Development' "
        "statt nur 'Tech'). Gezeigt werden nur die 20 Kategorien mit den meisten "
        "Bewerbungen, damit die Zahlen aussagekräftig bleiben."
    )
    fig_disc = px.bar(by_discipline, x="erfolgsquote_pct", y="discipline", orientation="h",
                       hover_data=["n"], color_discrete_sequence=[PINK])
    fig_disc.update_layout(**PLOTLY_LAYOUT, xaxis_title="Erfolgsquote (%)", yaxis_title="", height=520,
                            yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig_disc, use_container_width=True)

# --- Qualifiziert vs. Anstellungsart ------------------------------------
with col_right2:
    st.subheader("Qualifiziert vs. nicht qualifiziert")
    st.caption(
        "Bewerbungen werden vorab automatisch als 'qualifiziert' oder "
        "'nicht qualifiziert' eingestuft. Dieser Chart prüft, ob dieses Label "
        "tatsächlich etwas über den späteren Erfolg aussagt."
    )
    by_qualified["label"] = by_qualified["is_qualified_application"].map({0: "Nicht qualifiziert", 1: "Qualifiziert"})
    fig_qual = px.bar(by_qualified, x="label", y="erfolgsquote_pct", hover_data=["n"],
                       color_discrete_sequence=[PINK])
    fig_qual.update_layout(**PLOTLY_LAYOUT, xaxis_title="", yaxis_title="Erfolgsquote (%)", height=230)
    st.plotly_chart(fig_qual, use_container_width=True)

    st.subheader("Erfolgsquote nach Anstellungsart")
    st.caption(
        "Vergleicht z. B. Festanstellungen mit anderen Anstellungsarten: "
        "Wo ist die Chance auf eine erfolgreiche Einstellung höher?"
    )
    fig_type = px.bar(by_type, x="enquiry_type_categorized", y="erfolgsquote_pct", hover_data=["n"],
                       color_discrete_sequence=[PINK])
    fig_type.update_layout(**PLOTLY_LAYOUT, xaxis_title="", yaxis_title="Erfolgsquote (%)", height=230)
    st.plotly_chart(fig_type, use_container_width=True)

st.divider()

# --- Wann sind "genug" Bewerbungen da? -----------------------------------
st.header("Wann hat eine Stelle 'genug' Bewerbungen?")
st.markdown(
    """
**Methodik:** Für jede Stelle mit einer erfolgreichen Einstellung wurde geprüft, an welchem Tag die
mündliche Zusage des späteren Hires kam — das ist der Moment, an dem der Ausgang faktisch feststand.
Dann wurde gezählt: Wie viele Interviews und Bewerbungen (über alle Kandidat:innen dieser Stelle
hinweg) gab es bis zu diesem Zeitpunkt bereits? Das zeigt, ab wann eine Stelle im Rückblick
"ausreichend versorgt" war — nicht als feste Regel, sondern als Wahrscheinlichkeits-Aussage.
    """
)

st.subheader("Nach wie vielen Interviews stand der Hire meistens schon fest?")
st.caption(
    "Beispiel: Liegt die Linie bei 2 Interviews auf 56%, heißt das: Bei 56% aller Stellen mit "
    "einer Einstellung war der spätere Hire bereits nach höchstens 2 Interviews klar. "
    "Verglichen werden alle Fachbereiche zusammen mit den zwei angefragten Beispielen "
    "Tech und Craft & Construction (Handwerk & Bau)."
)
fig_cum = px.line(
    cum_interviews, x="interviews", y="anteil_pct", color="gruppe", markers=True,
    color_discrete_map={"Alle Fachbereiche": INK, "Tech": PINK, "Craft & Construction": "#B8135D"},
)
fig_cum.update_layout(**PLOTLY_LAYOUT, xaxis_title="Anzahl Interviews", yaxis_title="Anteil der Hires bereits erreicht (%)",
                       height=420, legend_title="")
st.plotly_chart(fig_cum, use_container_width=True)

st.markdown(
    "**Kernaussage:** Handwerk & Bau braucht im Schnitt spürbar weniger — bei der Hälfte dieser "
    "Stellen reichte **1 Interview**, um den späteren Hire zu finden. Bei Tech-Stellen braucht es "
    "typischerweise **2 Interviews**, und der Prozess zieht sich insgesamt länger (siehe Tabelle "
    "unten: mehr Bewerbungen nötig, bevor überhaupt interviewt wird)."
)

st.subheader("Nach Fachbereich sortiert")
st.caption(
    "Median = der Wert in der Mitte, weniger anfällig für Ausreißer als der Durchschnitt. "
    "Nur Fachbereiche mit mindestens 20 Einstellungen gezeigt, damit die Zahlen belastbar sind."
)
st.dataframe(
    area_threshold.rename(columns={
        "functional_area": "Fachbereich", "n_hires": "Hires (n)",
        "median_interviews": "Median Interviews bis Hire", "median_apps": "Median Bewerbungen bis Hire",
        "avg_score": "Ø Fit-Score Bewerberpool", "qualifiziert_pct": "Qualifiziert (%)",
    }),
    hide_index=True, use_container_width=True, height=420,
)

st.markdown(
    """
**Welche Faktoren spielen mit rein — und welche nicht?**

- **Fachbereich ist der stärkste Einflussfaktor.** Handwerk & Bau, Mobility und Helpers brauchen am
  wenigsten Interviews bis zum Hire (Median 1), während Education, Hospitality und Sales am meisten
  brauchen (Median 3–4). Das spiegelt vermutlich reale Marktunterschiede: In manchen Bereichen gibt es
  wenige, klar geeignete Kandidat:innen; in anderen (z. B. Sales, Marketing) ist die Auswahl größer und
  unübersichtlicher.
- **Bewerber-Qualität erklärt den Unterschied kaum.** Der durchschnittliche Fit-Score und der Anteil
  qualifizierter Bewerbungen im Kandidatenpool korrelieren nur sehr schwach mit der Anzahl nötiger
  Interviews (~0.1). Sprich: Es liegt nicht daran, dass Tech-Bewerber:innen "schlechter passen" — der
  Prozess selbst dauert dort einfach strukturell länger.
- **Tech braucht zusätzlich deutlich mehr Bewerbungen vorab** (Median 34 vs. 20 bei Handwerk & Bau),
  bevor überhaupt genug Interviews stattfinden. Eine pauschale "ab X Bewerbungen ist genug"-Regel würde
  Tech-Stellen also systematisch zu früh abschneiden und Handwerk-Stellen zu lange offen halten.

**Vorschlag für eine Definition:** Statt einer festen Zahl lohnt sich ein Schwellenwert *pro
Fachbereich*, z. B. der Median aus der Tabelle links als Richtwert — ergänzt um eine Sicherheitsmarge
(z. B. Median + 1 Interview), da bei exakt dem Median nur die Hälfte der Fälle abgedeckt ist.
    """
)

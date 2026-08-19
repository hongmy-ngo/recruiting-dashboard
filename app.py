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
discipline_interview_threshold = load("interviews_bis_hire_je_discipline")
discipline_threshold = load("bewerbungen_je_discipline")
stagnation_stopp = load("stagnation_stopp_je_discipline")
qualifiziert_vs_roh = load("qualifiziert_vs_roh_je_discipline")

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
    color_discrete_map={"Alle Fachbereiche": "#6B7280", "Tech": "#1D3E8C", "Craft & Construction": PINK},
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
        "empf_schwellenwert": "Empf. Schwellenwert (Median + 1)",
        "abdeckung_bei_median_pct": "Abdeckung bei Median (%)",
        "abdeckung_bei_schwellenwert_pct": "Abdeckung bei Schwellenwert (%)",
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
Fachbereich* — der Median aus der Tabelle als Richtwert, ergänzt um eine Sicherheitsmarge von
+1 Interview, da beim Median nur rund die Hälfte der Fälle abgedeckt ist (Spalte "Abdeckung bei
Median"). Die letzten beiden Spalten der Tabelle zeigen den Effekt konkret: Bei Handwerk & Bau
deckt der Schwellenwert von 2 Interviews bereits 73% aller Hires ab (statt 51% beim reinen Median),
bei Tech deckt ein Schwellenwert von 3 Interviews 69% ab. Als Faustregel über alle Fachbereiche
hinweg bringt "+1 Interview" die Abdeckung meist von rund 50–60% auf 60–78% — ein guter Kompromiss
zwischen "früh genug abschalten" und "den Hire nicht verpassen".
    """
)

st.subheader("Interview-Schwellenwert nach Discipline (statt nur Fachbereich)")
st.caption(
    "Gleiche Rechnung wie oben (Median + 1 Interview), aber auf Discipline-Ebene — der feineren "
    "Kategorie innerhalb eines Fachbereichs. Nur Disciplines mit mindestens 15 Einstellungen gezeigt."
)
st.dataframe(
    discipline_interview_threshold.rename(columns={
        "discipline": "Discipline", "functional_area": "Fachbereich", "n_hires": "Hires (n)",
        "median_interviews": "Median Interviews bis Hire",
        "empf_schwellenwert": "Empf. Schwellenwert (Median + 1)",
        "abdeckung_bei_median_pct": "Abdeckung bei Median (%)",
        "abdeckung_bei_schwellenwert_pct": "Abdeckung bei Schwellenwert (%)",
    }),
    hide_index=True, use_container_width=True, height=420,
)
st.markdown(
    "**Kernaussage:** Auch bei Interviews zeigt sich innerhalb der Fachbereiche nochmal Streuung — "
    "z. B. reicht bei Tech für Cybersecurity & Privacy Engineering im Median **1 Interview**, "
    "während IT Consulting **4** braucht. Ein Fachbereichs-weiter Schwellenwert glättet das weg."
)

st.divider()

# --- Bewerbungs-Schwellenwert je Discipline ------------------------------
st.header("Ab wie vielen Bewerbungen kann eine Anzeige schließen?")
st.markdown(
    """
**Gleiche Frage, andere Einheit:** Statt Interviews wird hier gezählt, wie viele Bewerbungen bis
zum Hire-Zeitpunkt bereits eingegangen waren — und zwar je **Discipline** (die feinere Kategorie
innerhalb eines Fachbereichs), weil sich das dort deutlich stärker unterscheidet als auf
Fachbereichs-Ebene. Bewerber-Qualität (Ø Fit-Score, Qualifiziert-Anteil) korreliert praktisch
nicht mit der benötigten Bewerbungszahl (r ≈ -0,01 bis -0,05) — die Discipline selbst ist auch
hier der Haupttreiber, nicht die Kandidat:innen-Qualität.
    """
)
st.caption(
    "Empf. Schwellenwert = Median × 1,5 (analog zur Interview-Regel, nur mit Faktor statt fixer "
    "Marge, weil die Bewerbungszahlen viel größer sind als Interviewzahlen). Nur Disciplines mit "
    "mindestens 15 Einstellungen gezeigt."
)
st.dataframe(
    discipline_threshold.rename(columns={
        "discipline": "Discipline", "functional_area": "Fachbereich", "n_hires": "Hires (n)",
        "median_apps": "Median Bewerbungen bis Hire",
        "empf_schwellenwert": "Empf. Schwellenwert (Median × 1,5)",
        "abdeckung_bei_median_pct": "Abdeckung bei Median (%)",
        "abdeckung_bei_schwellenwert_pct": "Abdeckung bei Schwellenwert (%)",
        "median_tage_bis_schwellenwert": "Median Tage bis Schwellenwert erreicht",
        "erreicht_schwellenwert_pct": "Stellen, die Schwellenwert je erreichen (%)",
    }),
    hide_index=True, use_container_width=True, height=420,
)
st.markdown(
    """
**Kernaussage:** Die Spanne reicht von Median 7 Bewerbungen (Fahrzeug- & Mobilitätstechnik) bis
Median 50 (Field Sales) — ein Faktor 7 zwischen den Extremen. Ein Fachbereichs-weiter Schwellenwert
verdeckt das: Innerhalb von Tech z. B. braucht IT Consulting (Median 47) mehr als das Dreifache an
Bewerbungen von DevOps & Cloud Engineering (Median 27). Die Faustregel "Median × 1,5" ist über fast
alle Disciplines hinweg stabil bei 60–80% Abdeckung — eignet sich also als generische Regel, wenn
man sie pro Discipline statt pro Fachbereich anwendet.

**Wie lange dauert das kalendarisch?** Die letzten beiden Spalten zeigen: Nur rund die Hälfte aller
Stellen erreicht ihren Schwellenwert überhaupt (viele bekommen nie genug Bewerbungen). Bei denen,
die ihn erreichen, schwankt die Dauer stark — von 26 Tagen (Grafikdesign / Webdesign / Mediendesign)
bis 225 Tagen (Taxation & Risk Management). IT Consulting braucht mit 211 Tagen am längsten unter
den Tech-Disciplines — mehr als 7 Monate für 70 Bewerbungen.
    """
)

st.divider()

# --- Alternative Stopp-Regeln: was tun, wenn der Schwellenwert kaum erreichbar ist? ---
st.header("Wenn der Schwellenwert kaum erreichbar ist: zwei getestete Alternativen")
st.markdown(
    """
Bei manchen Disciplines (z. B. Field Sales, Tech Projektmanagement, Einkauf, Rechtsanwälte & Juristen)
erreicht nur ein Drittel bis knapp die Hälfte der Stellen den empfohlenen Bewerbungs-Schwellenwert
überhaupt. Eine reine Bewerbungszahl-Regel läuft dort oft ins Leere. Zwei Alternativen wurden getestet.
    """
)

st.subheader("✅ Bewerbungs-Stillstand als Stopp-Signal")
st.caption(
    "Regel: Stoppen, wenn 30 Tage lang keine neue Bewerbung eingeht — statt bei einer festen "
    "Bewerbungszahl. Vorteil: löst IMMER aus (anders als die Bewerbungszahl-Regel, die bei vielen "
    "Stellen nie zündet), weil sie auf Inaktivität statt auf einen unerreichbaren Zielwert reagiert."
)
st.dataframe(
    stagnation_stopp.rename(columns={
        "discipline": "Discipline", "functional_area": "Fachbereich", "n_hires": "Hires (n)",
        "abdeckung_bewerbungszahl_regel_pct": "Abdeckung Bewerbungszahl-Regel (%)",
        "abdeckung_stagnation_pct": "Abdeckung Stillstands-Regel (%)",
        "median_tage_bis_stopp": "Median Tage bis Stopp",
        "differenz_pct": "Differenz (Prozentpunkte)",
    }),
    hide_index=True, use_container_width=True, height=420,
)
st.markdown(
    """
**Ergebnis:** Im Schnitt über alle Disciplines fast gleichauf (+1,5 Prozentpunkte), mit Ausschlägen in
beide Richtungen je Discipline. Der eigentliche Gewinn liegt nicht im Durchschnitt, sondern darin, dass
diese Regel **strukturell nicht scheitern kann** — sie braucht keinen erreichbaren Zielwert, sondern
reagiert direkt auf das, was tatsächlich passiert (oder eben nicht mehr passiert).
    """
)

st.subheader("❌ Qualifizierte statt rohe Bewerbungszahl als Ziel — getestet, verworfen")
st.caption(
    "Idee: Vielleicht ist eine kleinere Zielzahl (nur qualifizierte Bewerbungen statt aller) leichter "
    "erreichbar. Ergebnis: nein — verschlechtert die Erreichungsquote in praktisch jeder Discipline."
)
st.dataframe(
    qualifiziert_vs_roh.rename(columns={
        "discipline": "Discipline", "functional_area": "Fachbereich", "n_hires": "Hires (n)",
        "raw_schwellenwert": "Schwellenwert (roh)", "raw_erreicht_pct": "Erreicht, roh (%)",
        "qualifiziert_schwellenwert": "Schwellenwert (qualifiziert)",
        "qualifiziert_erreicht_pct": "Erreicht, qualifiziert (%)",
        "differenz_pct": "Differenz (Prozentpunkte)",
    }),
    hide_index=True, use_container_width=True, height=420,
)
st.markdown(
    "**Ergebnis:** In 0 von 55 Disciplines verbessert sich die Erreichungsquote — im Schnitt "
    "**-17 Prozentpunkte**. Selbst bei den vier eingangs schwierigen Disciplines (Field Sales, "
    "Tech Projektmanagement, Einkauf, Rechtsanwälte) wird es nicht besser. Grund: Qualifizierte "
    "Bewerbungen sind ein kleinerer, stärker schwankender Ausschnitt der Gesamtzahl — der Median "
    "als Zielwert wird dadurch relativ gesehen nicht verlässlicher erreicht, nur die absolute Zahl "
    "wird kleiner. **Nicht empfohlen.**"
)

"""RiskRadar: IT project risk management with Streamlit and SQLite."""

import streamlit as st

from risk_logic import calculate_score, risk_color, risk_level
from riskradar_db import add_project, add_risk, initialize_db, list_projects, list_risks, seed_sample_data


st.set_page_config(page_title="RiskRadar", page_icon="🎯", layout="wide")
initialize_db()
seed_sample_data()

st.title("🎯 RiskRadar")
st.caption("Risiken in IT-Projekten erkennen, bewerten und im Blick behalten.")

projects = list_projects()
risks = list_risks()
critical_risks = [r for r in risks if calculate_score(r["probability"], r["impact"]) >= 15]

metric_cols = st.columns(3)
metric_cols[0].metric("Projekte", len(projects))
metric_cols[1].metric("Risiken", len(risks))
metric_cols[2].metric("Kritische Risiken", len(critical_risks), help="Score ab 15 von 25")

overview, projects_tab, risks_tab = st.tabs(["Übersicht", "Projekte", "Risiken"])

with overview:
    st.subheader("Risiken mit höchstem Score")
    if not risks:
        st.info("Noch keine Risiken vorhanden. Lege im Tab „Risiken“ den ersten Eintrag an.")
    for risk in risks[:8]:
        score = calculate_score(risk["probability"], risk["impact"])
        color = risk_color(score)
        with st.container(border=True):
            left, right = st.columns([5, 1])
            left.markdown(f"**{risk['title']}** · {risk['project_name']}")
            left.caption(risk["description"])
            right.markdown(
                f'<div style="text-align:right;color:{color};font-weight:700">'
                f'{risk_level(score)} · {score}/25</div>', unsafe_allow_html=True
            )

with projects_tab:
    st.subheader("Projekte")
    with st.form("project_form", clear_on_submit=True):
        name = st.text_input("Projektname", placeholder="z. B. CRM-Einführung")
        description = st.text_area("Beschreibung")
        submitted = st.form_submit_button("Projekt anlegen", type="primary")
        if submitted:
            if not name.strip():
                st.error("Bitte gib einen Projektnamen ein.")
            else:
                try:
                    add_project(name, description)
                    st.success(f"Projekt „{name.strip()}“ wurde angelegt.")
                    st.rerun()
                except Exception as exc:
                    if "UNIQUE constraint failed" in str(exc):
                        st.error("Ein Projekt mit diesem Namen existiert bereits.")
                    else:
                        raise
    if projects:
        for project in projects:
            with st.container(border=True):
                st.markdown(f"**{project['name']}**")
                st.write(project["description"] or "Keine Beschreibung hinterlegt.")
                project_risk_count = sum(r["project_id"] == project["id"] for r in risks)
                st.caption(f"{project_risk_count} Risiken")

with risks_tab:
    st.subheader("Risiken erfassen und bewerten")
    if not projects:
        st.info("Lege zuerst ein Projekt an.")
    else:
        project_lookup = {p["name"]: p["id"] for p in projects}
        with st.form("risk_form", clear_on_submit=True):
            selected_name = st.selectbox("Projekt", list(project_lookup))
            title = st.text_input("Risikotitel")
            description = st.text_area("Beschreibung", key="risk_description")
            probability = st.select_slider("Eintrittswahrscheinlichkeit", options=[1, 2, 3, 4, 5], value=3)
            impact = st.select_slider("Schadensauswirkung", options=[1, 2, 3, 4, 5], value=3)
            score = calculate_score(probability, impact)
            st.markdown(f"**Aktueller Score: {score}/25 · {risk_level(score)}**")
            submitted = st.form_submit_button("Risiko speichern", type="primary")
            if submitted:
                if not title.strip():
                    st.error("Bitte gib einen Risikotitel ein.")
                else:
                    add_risk(project_lookup[selected_name], title, description, probability, impact)
                    st.success("Risiko wurde gespeichert.")
                    st.rerun()

    st.divider()
    filter_options = ["Alle Projekte"] + [p["name"] for p in projects]
    selected_filter = st.selectbox("Risiken filtern", filter_options, key="risk_filter")
    filtered_risks = list_risks(None if selected_filter == "Alle Projekte" else project_lookup[selected_filter]) if projects else []
    if not filtered_risks:
        st.info("Für diese Auswahl sind keine Risiken vorhanden.")
    for risk in filtered_risks:
        score = calculate_score(risk["probability"], risk["impact"])
        color = risk_color(score)
        with st.container(border=True):
            cols = st.columns([4, 2, 1])
            cols[0].markdown(f"**{risk['title']}**")
            cols[0].caption(f"{risk['project_name']} · {risk['description']}")
            cols[1].write(f"Wahrscheinlichkeit {risk['probability']}/5 · Auswirkung {risk['impact']}/5")
            cols[2].markdown(
                f'<div style="color:{color};font-weight:700">{risk_level(score)}<br>{score}/25</div>',
                unsafe_allow_html=True,
            )

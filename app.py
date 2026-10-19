"""RiskRadar: IT project risk management with Streamlit and SQLite."""

import importlib

import streamlit as st

import risk_logic

# Streamlit reruns this script in one process. Refresh an older cached module
# when the matrix helper was added while that process was already running.
if not hasattr(risk_logic, "group_risks_by_cell"):
    risk_logic = importlib.reload(risk_logic)

from risk_logic import calculate_score, group_risks_by_cell, risk_color, risk_level
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

overview, projects_tab, risks_tab, matrix_tab = st.tabs(
    ["Übersicht", "Projekte", "Risiken", "Risikomatrix"]
)

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

with matrix_tab:
    st.subheader("5×5-Risikomatrix")
    st.caption("Wähle ein Feld, um alle dort eingetragenen Risiken anzuzeigen.")
    if projects:
        matrix_project_names = ["Alle Projekte"] + [project["name"] for project in projects]
        matrix_project = st.selectbox(
            "Projektfilter", matrix_project_names, key="matrix_project_filter"
        )
        matrix_project_id = (
            None if matrix_project == "Alle Projekte"
            else next(project["id"] for project in projects if project["name"] == matrix_project)
        )
        matrix_risks = list_risks(matrix_project_id)
    else:
        matrix_risks = []

    risks_by_cell = group_risks_by_cell(matrix_risks)
    st.markdown("**Eintrittswahrscheinlichkeit ↑**")
    for probability in range(5, 0, -1):
        row = st.columns([0.8, 1, 1, 1, 1, 1])
        row[0].markdown(f"**{probability}**")
        for column_index, impact in enumerate(range(1, 6), start=1):
            cell_risks = risks_by_cell.get((probability, impact), [])
            score = calculate_score(probability, impact)
            level = risk_level(score)
            marker = {"Niedrig": "🟩", "Mittel": "🟨", "Hoch": "🟥"}[level]
            count_label = f"{len(cell_risks)} Risiko" if len(cell_risks) == 1 else f"{len(cell_risks)} Risiken"
            if row[column_index].button(
                f"{marker} {score}/25\n{count_label}",
                key=f"matrix_cell_{probability}_{impact}",
                use_container_width=True,
                help=f"Wahrscheinlichkeit {probability}, Auswirkung {impact}: {level}",
            ):
                st.session_state["selected_matrix_cell"] = (probability, impact)

    impact_labels = st.columns([0.8, 1, 1, 1, 1, 1])
    impact_labels[0].markdown("**Auswirkung →**")
    for impact in range(1, 6):
        impact_labels[impact].markdown(f"**{impact}**")
    st.caption("🟩 Niedrig (Score 1–6)　 🟨 Mittel (7–14)　 🟥 Hoch (15–25)")

    selected_cell = st.session_state.get("selected_matrix_cell")
    if selected_cell:
        selected_probability, selected_impact = selected_cell
        selected_risks = risks_by_cell.get(selected_cell, [])
        st.markdown(
            f"#### Feld: Wahrscheinlichkeit {selected_probability} × "
            f"Auswirkung {selected_impact} · Score {selected_probability * selected_impact}/25"
        )
        if selected_risks:
            for risk in selected_risks:
                with st.container(border=True):
                    st.text(f"{risk['title']} · {risk['project_name']}")
                    st.write(risk["description"] or "Keine Beschreibung hinterlegt.")
        else:
            st.info("In diesem Feld liegen für den gewählten Projektfilter keine Risiken.")
    elif not matrix_risks:
        st.info("Für den gewählten Projektfilter sind keine Risiken vorhanden.")

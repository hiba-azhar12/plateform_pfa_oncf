from urllib.parse import urlparse

import streamlit as st

from utils.style import appliquer_style, logo_pda_sidebar


def _est_page_accueil():

    try:
        chemin = urlparse(st.context.url).path.rstrip("/")
    except Exception:
        return True
    dernier_segment = chemin.rsplit("/", 1)[-1]
    return dernier_segment in ("", "accueil")


st.set_page_config(
    page_title="Plateforme ONCF - Performance Commerciale",
    layout="wide",
    initial_sidebar_state="expanded",
)

appliquer_style()

page_accueil = st.Page("pages/accueil.py", title="Accueil", url_path="accueil", default=True)

pages_predictions = [
    page_accueil,
    st.Page("pages/predictions/nouvelles_predictions.py", title="Nouvelles Prédictions"),
]

pages_ventes = [
    st.Page("pages/ventes/dashboard_ventes.py", title="Dashboard Ventes"),
    st.Page("pages/ventes/anomalies_ventes.py", title="Anomalies Ventes"),
    st.Page("pages/ventes/explicabilite_ventes.py", title="Explicabilité Ventes"),
]

pages_controles = [
    st.Page("pages/controles/dashboard_controles.py", title="Dashboard Contrôles"),
    st.Page("pages/controles/anomalies_controles.py", title="Anomalies Contrôles"),
    st.Page("pages/controles/explicabilite_controles.py", title="Explicabilité Contrôles"),
]

pages_transverse = [
    st.Page("pages/transverse/comparaison_inter_annees.py", title="Comparaison inter-années"),
    st.Page("pages/transverse/rapports.py", title="Rapports"),
    st.Page("pages/transverse/chatbot.py", title="Chatbot"),
    st.Page("pages/transverse/guide_chatbot.py", title="Guide du chatbot"),
    st.Page("pages/transverse/administration.py", title="Administration"),
]

accueil_detectee = _est_page_accueil()
print(f"[app.py] st.context.url={st.context.url!r} accueil_detectee={accueil_detectee}")

navigation = st.navigation(
    {
        "Prédictions": pages_predictions,
        "Ventes": pages_ventes,
        "Contrôles": pages_controles,
        "Analyse transverse": pages_transverse,
    },
    position="hidden" if accueil_detectee else "sidebar",
)

if not accueil_detectee:
    logo_pda_sidebar()

navigation.run()
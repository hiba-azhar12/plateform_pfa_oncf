from urllib.parse import urlparse

import streamlit as st

from utils.style import appliquer_style, logo_pda_sidebar


def _est_page_accueil():
    """Determine si l'URL demandee correspond a la page d'accueil, avant
    meme de construire la navigation, pour ne jamais generer le menu complet
    dans ce cas (plutot que de le generer puis tenter de le cacher, ce qui
    laissait un flash visible)."""
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

pages_predictions_visibles = [
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

if accueil_detectee:
    # Toutes les pages restent enregistrees (necessaire pour que
    # st.switch_page fonctionne depuis l'accueil), mais aucun menu n'est
    # construit (position="hidden") : rien a cacher, donc pas de flash.
    navigation = st.navigation(
        {
            "Prédictions": [page_accueil] + pages_predictions_visibles,
            "Ventes": pages_ventes,
            "Contrôles": pages_controles,
            "Analyse transverse": pages_transverse,
        },
        position="hidden",
    )
else:
    # "Accueil" n'est volontairement pas inclus dans la liste affichee ici :
    # on y accede via l'URL racine ou le logo, pas via le menu.
    navigation = st.navigation(
        {
            "Prédictions": pages_predictions_visibles,
            "Ventes": pages_ventes,
            "Contrôles": pages_controles,
            "Analyse transverse": pages_transverse,
        },
        position="sidebar",
    )
    logo_pda_sidebar()

navigation.run()
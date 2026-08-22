import streamlit as st

from utils.style import appliquer_style, logo_pda_sidebar

st.set_page_config(
    page_title="Plateforme ONCF - Performance Commerciale",
    layout="wide",
    initial_sidebar_state="expanded",
)

appliquer_style()

page_accueil = st.Page("pages/accueil.py", title="Accueil", url_path="accueil", default=True)
page_nouvelles_predictions = st.Page("pages/predictions/nouvelles_predictions.py", title="Nouvelles Prédictions")

page_dashboard_ventes = st.Page("pages/ventes/dashboard_ventes.py", title="Dashboard Ventes")
page_anomalies_ventes = st.Page("pages/ventes/anomalies_ventes.py", title="Anomalies Ventes")
page_explicabilite_ventes = st.Page("pages/ventes/explicabilite_ventes.py", title="Explicabilité Ventes")

page_dashboard_controles = st.Page("pages/controles/dashboard_controles.py", title="Dashboard Contrôles")
page_anomalies_controles = st.Page("pages/controles/anomalies_controles.py", title="Anomalies Contrôles")
page_explicabilite_controles = st.Page("pages/controles/explicabilite_controles.py", title="Explicabilité Contrôles")

page_comparaison = st.Page("pages/transverse/comparaison_inter_annees.py", title="Comparaison inter-années")
page_rapports = st.Page("pages/transverse/rapports.py", title="Rapports")
page_chatbot = st.Page("pages/transverse/chatbot.py", title="Chatbot")
page_guide_chatbot = st.Page("pages/transverse/guide_chatbot.py", title="Guide du chatbot")
page_administration = st.Page("pages/transverse/administration.py", title="Administration")

navigation = st.navigation(
    {
        "Prédictions": [page_accueil, page_nouvelles_predictions],
        "Ventes": [page_dashboard_ventes, page_anomalies_ventes, page_explicabilite_ventes],
        "Contrôles": [page_dashboard_controles, page_anomalies_controles, page_explicabilite_controles],
        "Analyse transverse": [page_comparaison, page_rapports, page_chatbot, page_guide_chatbot, page_administration],
    },
    position="hidden",
)

with st.sidebar:
    st.markdown('<div class="menu-section-titre menu-section-titre-premiere">Prédictions</div>', unsafe_allow_html=True)
    st.page_link(page_nouvelles_predictions, label="Nouvelles Prédictions")

    st.markdown('<div class="menu-section-titre">Ventes</div>', unsafe_allow_html=True)
    st.page_link(page_dashboard_ventes, label="Dashboard Ventes")
    st.page_link(page_anomalies_ventes, label="Anomalies Ventes")
    st.page_link(page_explicabilite_ventes, label="Explicabilité Ventes")

    st.markdown('<div class="menu-section-titre">Contrôles</div>', unsafe_allow_html=True)
    st.page_link(page_dashboard_controles, label="Dashboard Contrôles")
    st.page_link(page_anomalies_controles, label="Anomalies Contrôles")
    st.page_link(page_explicabilite_controles, label="Explicabilité Contrôles")

    st.markdown('<div class="menu-section-titre">Analyse transverse</div>', unsafe_allow_html=True)
    st.page_link(page_comparaison, label="Comparaison inter-années")
    st.page_link(page_rapports, label="Rapports")
    st.page_link(page_chatbot, label="Chatbot")
    st.page_link(page_guide_chatbot, label="Guide du chatbot")
    st.page_link(page_administration, label="Administration")

logo_pda_sidebar()

navigation.run()
import streamlit as st

from utils.style import appliquer_style

st.set_page_config(
    page_title="Plateforme ONCF - Performance Commerciale",
    layout="wide",
    initial_sidebar_state="expanded",
)

appliquer_style()

pages_predictions = [
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
]

navigation = st.navigation({
    "Prédictions": pages_predictions,
    "Ventes": pages_ventes,
    "Contrôles": pages_controles,
    "Analyse transverse": pages_transverse,
})

navigation.run()

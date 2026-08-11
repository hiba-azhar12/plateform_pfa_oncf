import base64
import os

import streamlit as st

PALETTE = {
    "navy": "#2E3540",
    "navy_fonce": "#242A33",
    "blue": "#13315C",
    "steel": "#3A6EA5",
    "orange": "#F58220",
    "orange_fonce": "#D96A0F",
    "red": "#C8102E",
    "amber": "#B8860B",
    "green": "#1E7145",
    "bg": "#F5F1E8",
    "surface": "#FFFFFF",
    "border": "#E4DCC8",
    "border_carte": "#EAD1A6",
    "text": "#242A33",
    "muted": "#6B7280",
}

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER_ASSETS = os.path.join(RACINE, "assets")

CHEMIN_LOGO_ONCF = os.path.join(DOSSIER_ASSETS, "oncf.png")
CHEMIN_LOGO_TRAIN = os.path.join(DOSSIER_ASSETS, "train.png")
CHEMIN_LOGO_PDA = os.path.join(DOSSIER_ASSETS, "pda.png")


@st.cache_data(show_spinner=False)
def _image_base64(chemin):
    if not os.path.isfile(chemin):
        return None
    with open(chemin, "rb") as fichier:
        return base64.b64encode(fichier.read()).decode("utf-8")


def appliquer_style():
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }}

        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}

        header[data-testid="stHeader"] {{
            background-color: transparent;
            height: 0rem;
            min-height: 0rem;
        }}

        div[data-testid="stAppViewContainer"] {{
            background-color: {PALETTE["bg"]};
        }}

        .stApp {{
            background-color: {PALETTE["bg"]};
        }}

        section[data-testid="stMain"] .block-container,
        div[data-testid="stAppViewBlockContainer"] {{
            padding-top: 0rem !important;
            max-width: 1320px;
        }}

        section[data-testid="stSidebar"] {{
            background-color: {PALETTE["navy"]};
        }}

        section[data-testid="stSidebar"] > div:first-child {{
            padding-top: 1.2rem;
        }}

        section[data-testid="stSidebar"] * {{
            color: #E8ECF2 !important;
        }}

        section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"],
        section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {{
            border-left: 3px solid transparent;
            border-radius: 0;
            padding-left: 12px;
            transition: border-color 0.15s ease, color 0.15s ease;
        }}

        section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover,
        section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {{
            border-left-color: rgba(245, 130, 32, 0.5);
        }}

        section[data-testid="stSidebar"] [aria-current="page"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-selected="true"] {{
            border-left-color: {PALETTE["orange"]} !important;
            font-weight: 700;
        }}

        section[data-testid="stSidebar"] [aria-current="page"] * {{
            color: {PALETTE["orange"]} !important;
        }}

        .logo-pda-sidebar {{
            display: flex;
            justify-content: center;
            padding: 26px 18px 20px 18px;
            margin-top: 30px;
        }}

        .logo-pda-sidebar img {{
            width: 96px;
            height: auto;
        }}

        .bandeau-marque {{
            background: {PALETTE["navy"]};
            padding: 0;
            margin: 0 0 0 0;
            overflow: hidden;
            display: flex;
            align-items: center;
            height: 78px;
        }}

        .bandeau-marque-logo {{
            display: flex;
            align-items: center;
            padding: 0 26px;
            height: 100%;
            white-space: nowrap;
        }}

        .bandeau-marque-logo img {{
            height: 40px;
            width: auto;
        }}

        .bandeau-marque-train {{
            flex: 1;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            overflow: hidden;
            padding-right: 0;
        }}

        .bandeau-marque-train img {{
            height: 82%;
            width: auto;
            object-fit: contain;
        }}

        .bandeau-accent {{
            background: {PALETTE["orange"]};
            height: 10px;
            width: 100%;
        }}

        .entete-page {{
            padding: 22px 28px 6px 28px;
        }}

        .entete-page h1 {{
            color: {PALETTE["text"]};
            font-weight: 700;
            font-size: 1.5rem;
            margin: 0 0 4px 0;
        }}

        .entete-page p {{
            color: {PALETTE["muted"]};
            font-size: 0.92rem;
            margin: 0;
        }}

        div[data-testid="stMetric"] {{
            background-color: {PALETTE["surface"]};
            border: 1px solid {PALETTE["border_carte"]};
            border-radius: 10px;
            padding: 16px 18px;
        }}

        div[data-testid="stMetricLabel"] {{
            color: {PALETTE["muted"]};
        }}

        div[data-testid="stMetricValue"] {{
            color: {PALETTE["navy"]};
            font-weight: 700;
        }}

        .carte-fraude div[data-testid="stMetricValue"] {{
            color: {PALETTE["red"]};
        }}

        .st-key-panneau_selection {{
            background-color: {PALETTE["orange_fonce"]} !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 18px 20px !important;
        }}

        div[class*="st-key-panneau_selection"] {{
            background-color: {PALETTE["orange_fonce"]} !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 18px 20px !important;
        }}

        div[data-testid="stVerticalBlockBorderWrapper"]:has(div[class*="st-key-panneau_selection"]) {{
            background-color: {PALETTE["orange_fonce"]} !important;
            border: none !important;
            border-radius: 10px !important;
        }}

        div[data-testid="stVerticalBlockBorderWrapper"]:has(div[class*="st-key-panneau_selection"]) > div {{
            background-color: transparent !important;
        }}

        .st-key-panneau_selection *:not(.react-aria-ComboBox):not(.react-aria-ComboBox *),
        div[class*="st-key-panneau_selection"] *:not(.react-aria-ComboBox):not(.react-aria-ComboBox *) {{
            color: #FFFFFF !important;
        }}

        .st-key-panneau_selection .react-aria-ComboBox,
        .st-key-panneau_selection .react-aria-ComboBox *,
        div[class*="st-key-panneau_selection"] .react-aria-ComboBox,
        div[class*="st-key-panneau_selection"] .react-aria-ComboBox * {{
            color: {PALETTE["text"]} !important;
            -webkit-text-fill-color: {PALETTE["text"]} !important;
            background-color: #FFFFFF !important;
            opacity: 1 !important;
            visibility: visible !important;
        }}

        .st-key-panneau_selection .react-aria-ComboBox,
        div[class*="st-key-panneau_selection"] .react-aria-ComboBox {{
            border-radius: 6px !important;
        }}

        .st-key-panneau_selection div[data-baseweb="select"],
        .st-key-panneau_selection div[data-baseweb="select"] *,
        div[class*="st-key-panneau_selection"] div[data-baseweb="select"],
        div[class*="st-key-panneau_selection"] div[data-baseweb="select"] * {{
            color: {PALETTE["text"]} !important;
            -webkit-text-fill-color: {PALETTE["text"]} !important;
            background-color: #FFFFFF !important;
        }}

        .bandeau-statut {{
            border-radius: 8px;
            padding: 14px 18px;
            font-size: 0.95rem;
            margin-bottom: 20px;
            border-left: 5px solid;
        }}

        .bandeau-statut-succes {{
            background-color: #EAF4EE;
            border-color: {PALETTE["green"]};
            color: #16502F;
        }}

        .bandeau-statut-avertissement {{
            background-color: #FBF3E3;
            border-color: {PALETTE["amber"]};
            color: #6B4E00;
        }}

        .bandeau-statut-erreur {{
            background-color: #FBEAEC;
            border-color: {PALETTE["red"]};
            color: #7A0E1E;
        }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid {PALETTE["border"]};
            border-radius: 8px;
        }}

        .stButton > button, .stDownloadButton > button {{
            background-color: {PALETTE["orange"]};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            padding: 0.5rem 1.1rem;
        }}

        .stButton > button:hover, .stDownloadButton > button:hover {{
            background-color: {PALETTE["orange_fonce"]};
            color: #FFFFFF;
        }}

        div[data-baseweb="select"] > div {{
            border-color: {PALETTE["border"]};
            border-radius: 6px;
        }}

        div[data-baseweb="select"] > div:focus-within {{
            border-color: {PALETTE["orange"]} !important;
            box-shadow: 0 0 0 1px {PALETTE["orange"]} !important;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: 22px;
            border-bottom: 1px solid {PALETTE["border"]};
        }}

        .stTabs [data-baseweb="tab"] {{
            background-color: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            border-radius: 0;
            padding: 8px 2px;
            color: {PALETTE["muted"]};
        }}

        .stTabs [aria-selected="true"] {{
            background-color: transparent !important;
            color: {PALETTE["text"]} !important;
            border-bottom: 3px solid {PALETTE["orange"]} !important;
            font-weight: 600;
        }}

        [data-testid="stExpander"] {{
            border: none;
            box-shadow: none;
        }}

        [data-testid="stExpander"] summary {{
            background-color: {PALETTE["orange_fonce"]} !important;
            color: #FFFFFF !important;
            border-radius: 8px 8px 0 0;
            padding: 10px 16px;
            font-weight: 600;
        }}

        [data-testid="stExpander"] summary p {{
            color: #FFFFFF !important;
            font-weight: 600;
        }}

        [data-testid="stExpander"] summary svg {{
            fill: #FFFFFF !important;
        }}

        [data-testid="stExpander"] details {{
            border: 1px solid {PALETTE["orange_fonce"]};
            border-radius: 8px;
            overflow: hidden;
        }}

        [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
            background-color: #FFFFFF;
            border-top: none;
            padding: 16px;
        }}

        [data-testid="stChatMessage"] {{
            border-radius: 12px;
            border: 1px solid {PALETTE["border"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def bandeau_marque():
    logo_oncf = _image_base64(CHEMIN_LOGO_ONCF)
    logo_train = _image_base64(CHEMIN_LOGO_TRAIN)

    bloc_logo = (
        f'<img src="data:image/png;base64,{logo_oncf}" alt="ONCF" />'
        if logo_oncf else '<span style="color:white;font-weight:800;font-size:1.4rem;">ONCF</span>'
    )
    bloc_train = (
        f'<img src="data:image/png;base64,{logo_train}" alt="Train ONCF" />'
        if logo_train else ""
    )

    st.markdown(
        f"""
        <div class="bandeau-marque">
            <div class="bandeau-marque-logo">{bloc_logo}</div>
            <div class="bandeau-marque-train">{bloc_train}</div>
        </div>
        <div class="bandeau-accent"></div>
        """,
        unsafe_allow_html=True,
    )


def logo_pda_sidebar():
    logo_pda = _image_base64(CHEMIN_LOGO_PDA)
    if not logo_pda:
        return
    st.sidebar.markdown(
        f"""
        <div class="logo-pda-sidebar">
            <img src="data:image/png;base64,{logo_pda}" alt="PDA" />
        </div>
        """,
        unsafe_allow_html=True,
    )


def entete(titre, sous_titre=""):
    bandeau_marque()
    st.markdown(
        f"""
        <div class="entete-page">
            <h1>{titre}</h1>
            <p>{sous_titre}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def bandeau_statut(niveau, message):
    classes = {
        "succes": "bandeau-statut-succes",
        "avertissement": "bandeau-statut-avertissement",
        "erreur": "bandeau-statut-erreur",
    }
    st.markdown(
        f'<div class="bandeau-statut {classes.get(niveau, "bandeau-statut-avertissement")}">{message}</div>',
        unsafe_allow_html=True,
    )
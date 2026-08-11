import streamlit as st

PALETTE = {
    "navy": "#0B2545",
    "blue": "#13315C",
    "steel": "#3A6EA5",
    "orange": "#F58220",
    "orange_fonce": "#D96A0F",
    "red": "#C8102E",
    "amber": "#B8860B",
    "green": "#1E7145",
    "bg": "#F4F6F9",
    "surface": "#FFFFFF",
    "border": "#DDE2E8",
    "text": "#1C1F26",
    "muted": "#5B6472",
}

import base64
import os

import streamlit as st

PALETTE = {
    "navy": "#0B2545",
    "blue": "#13315C",
    "steel": "#3A6EA5",
    "orange": "#F58220",
    "orange_fonce": "#D96A0F",
    "red": "#C8102E",
    "amber": "#B8860B",
    "green": "#1E7145",
    "bg": "#F4F6F9",
    "surface": "#FFFFFF",
    "border": "#DDE2E8",
    "text": "#1C1F26",
    "muted": "#5B6472",
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
        }}

        .stApp {{
            background-color: {PALETTE["bg"]};
        }}

        .block-container {{
            padding-top: 1.2rem;
            max-width: 1280px;
        }}

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {{
            background-color: {PALETTE["navy"]};
            border-right: 3px solid {PALETTE["orange"]};
        }}

        section[data-testid="stSidebar"] * {{
            color: #E8ECF2 !important;
        }}

        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] {{
            padding-top: 6px;
        }}

        section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"],
        section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {{
            border-radius: 6px;
            margin: 1px 8px;
            transition: background-color 0.15s ease;
        }}

        section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover,
        section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {{
            background-color: rgba(245, 130, 32, 0.16) !important;
        }}

        section[data-testid="stSidebar"] [aria-current="page"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-selected="true"] {{
            background-color: {PALETTE["orange"]} !important;
            font-weight: 600;
        }}

        section[data-testid="stSidebar"] [aria-current="page"] * {{
            color: #FFFFFF !important;
        }}

        .logo-pda-sidebar {{
            position: sticky;
            bottom: 0;
            left: 0;
            padding: 14px 18px;
            margin-top: 40px;
            border-top: 1px solid rgba(255,255,255,0.15);
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .logo-pda-icone {{
            width: 32px;
            height: auto;
            flex-shrink: 0;
        }}

        .logo-pda-texte {{
            font-size: 0.78rem;
            color: #B9C2D0 !important;
            line-height: 1.15;
        }}

        /* ---------- Bandeau de marque (haut de chaque page) ---------- */
        .bandeau-marque {{
            background: {PALETTE["navy"]};
            border-radius: 10px;
            padding: 0;
            margin-bottom: 18px;
            overflow: hidden;
            display: flex;
            align-items: center;
            height: 64px;
        }}

        .bandeau-marque-logo {{
            display: flex;
            align-items: center;
            padding: 0 22px;
            height: 100%;
            background: rgba(0,0,0,0.18);
            white-space: nowrap;
        }}

        .bandeau-marque-logo img {{
            height: 32px;
            width: auto;
        }}

        .bandeau-marque-train {{
            flex: 1;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            overflow: hidden;
            padding-right: 6px;
        }}

        .bandeau-marque-train img {{
            height: 68%;
            width: auto;
            object-fit: contain;
        }}

        /* ---------- Titre de page (bandeau orange) ---------- */
        .entete-page {{
            background: linear-gradient(90deg, {PALETTE["orange"]}, {PALETTE["orange_fonce"]});
            border-radius: 10px;
            padding: 16px 22px;
            margin-bottom: 22px;
        }}

        .entete-page h1 {{
            color: #FFFFFF;
            font-weight: 700;
            font-size: 1.5rem;
            margin-bottom: 2px;
        }}

        .entete-page p {{
            color: rgba(255,255,255,0.88);
            font-size: 0.92rem;
            margin: 0;
        }}

        /* ---------- Cartes / conteneurs ---------- */
        div[data-testid="stMetric"] {{
            background-color: {PALETTE["surface"]};
            border: 1px solid {PALETTE["border"]};
            border-radius: 10px;
            padding: 16px 18px;
            box-shadow: 0 1px 3px rgba(11, 37, 69, 0.06);
        }}

        div[data-testid="stMetricLabel"] {{
            color: {PALETTE["muted"]};
        }}

        div[data-testid="stMetricValue"] {{
            color: {PALETTE["navy"]};
            font-weight: 700;
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 10px !important;
        }}

        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {{
            box-shadow: 0 1px 3px rgba(11, 37, 69, 0.06);
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

        .carte-fraude div[data-testid="stMetricValue"] {{
            color: {PALETTE["red"]};
        }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid {PALETTE["border"]};
            border-radius: 8px;
        }}

        /* ---------- Boutons ---------- */
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

        /* ---------- Selects / dropdowns (rappel du panneau orange du gabarit) ---------- */
        div[data-baseweb="select"] > div {{
            border-color: {PALETTE["border"]};
            border-radius: 6px;
        }}

        div[data-baseweb="select"] > div:focus-within {{
            border-color: {PALETTE["orange"]} !important;
            box-shadow: 0 0 0 1px {PALETTE["orange"]} !important;
        }}

        /* ---------- Onglets ---------- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
        }}

        .stTabs [data-baseweb="tab"] {{
            background-color: {PALETTE["surface"]};
            border: 1px solid {PALETTE["border"]};
            border-radius: 6px 6px 0 0;
            padding: 8px 18px;
            color: {PALETTE["muted"]};
        }}

        .stTabs [aria-selected="true"] {{
            background-color: {PALETTE["navy"]};
            color: #FFFFFF !important;
            border-bottom: 3px solid {PALETTE["orange"]};
        }}

        /* ---------- Chat ---------- */
        [data-testid="stChatMessage"] {{
            border-radius: 12px;
            border: 1px solid {PALETTE["border"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def bandeau_marque():
    """Bandeau de marque décoratif en haut de chaque page (logo ONCF + train)."""
    logo_oncf = _image_base64(CHEMIN_LOGO_ONCF)
    logo_train = _image_base64(CHEMIN_LOGO_TRAIN)

    bloc_logo = (
        f'<img src="data:image/png;base64,{logo_oncf}" alt="ONCF" />'
        if logo_oncf else '<span style="color:white;font-weight:800;">ONCF</span>'
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
        """,
        unsafe_allow_html=True,
    )


def logo_pda_sidebar():
    """Logo PDA épinglé en bas de la barre latérale."""
    logo_pda = _image_base64(CHEMIN_LOGO_PDA)
    bloc_icone = (
        f'<img class="logo-pda-icone" src="data:image/png;base64,{logo_pda}" alt="PDA" />'
        if logo_pda else '<div class="logo-pda-icone"></div>'
    )
    st.sidebar.markdown(
        f"""
        <div class="logo-pda-sidebar">
            {bloc_icone}
            <div class="logo-pda-texte">Plateforme<br>Performance Commerciale</div>
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
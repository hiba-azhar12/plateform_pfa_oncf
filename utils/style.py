import streamlit as st

PALETTE = {
    "navy": "#0B2545",
    "blue": "#13315C",
    "steel": "#3A6EA5",
    "red": "#C8102E",
    "amber": "#B8860B",
    "green": "#1E7145",
    "bg": "#F4F6F9",
    "surface": "#FFFFFF",
    "border": "#DDE2E8",
    "text": "#1C1F26",
    "muted": "#5B6472",
}


def appliquer_style():
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }}

        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        

        .stApp {{
            background-color: {PALETTE["bg"]};
        }}

        section[data-testid="stSidebar"] {{
            background-color: {PALETTE["navy"]};
        }}

        section[data-testid="stSidebar"] * {{
            color: #E8ECF2 !important;
        }}

        section[data-testid="stSidebar"] .stRadio label,
        section[data-testid="stSidebar"] a {{
            color: #E8ECF2 !important;
        }}

        div[data-testid="stMetric"] {{
            background-color: {PALETTE["surface"]};
            border: 1px solid {PALETTE["border"]};
            border-radius: 6px;
            padding: 16px 18px;
        }}

        div[data-testid="stMetricLabel"] {{
            color: {PALETTE["muted"]};
        }}

        div[data-testid="stMetricValue"] {{
            color: {PALETTE["navy"]};
        }}

        .entete-page {{
            border-bottom: 3px solid {PALETTE["navy"]};
            padding-bottom: 14px;
            margin-bottom: 24px;
        }}

        .entete-page h1 {{
            color: {PALETTE["navy"]};
            font-weight: 600;
            font-size: 1.7rem;
            margin-bottom: 2px;
        }}

        .entete-page p {{
            color: {PALETTE["muted"]};
            font-size: 0.95rem;
            margin: 0;
        }}

        .bandeau-statut {{
            border-radius: 6px;
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
            border-radius: 6px;
        }}

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
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def entete(titre, sous_titre=""):
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

import streamlit as st

from utils.style import CHEMIN_LOGO_ONCF, CHEMIN_LOGO_PDA, CHEMIN_LOGO_TRAIN, PALETTE, _image_base64

logo_oncf_b64 = _image_base64(CHEMIN_LOGO_ONCF)
logo_pda_b64 = _image_base64(CHEMIN_LOGO_PDA)
logo_train_b64 = _image_base64(CHEMIN_LOGO_TRAIN)

st.markdown(
    f"""
    <style>
    section.stMain .block-container,
    div[data-testid="stMainBlockContainer"],
    div[data-testid="stAppViewBlockContainer"] {{
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
    }}

    div[data-testid="stAppViewContainer"],
    .stApp {{
        background-color: {PALETTE["navy"]} !important;
    }}

    div[data-testid="stAppViewContainer"]:has(.st-key-accueil_page) section[data-testid="stSidebar"] {{
        display: none !important;
    }}

    div[data-testid="stAppViewContainer"]:has(.st-key-accueil_page) div[data-testid="stSidebarCollapsedControl"] {{
        display: none !important;
    }}

    .st-key-accueil_page [data-testid="stVerticalBlock"] {{
        gap: 0 !important;
        min-height: 100vh;
    }}

    .accueil-topbar {{
        padding: 38px 0 0 68px;
    }}

    .accueil-topbar img {{
        height: 75px;
        width: auto;
    }}

    .accueil-pda {{
        position: fixed;
        top: 30px;
        right: 170px;
        width: 250px;
        transform: rotate(15deg);
        z-index: 1;
        pointer-events: none;
    }}

    .accueil-pda img {{
        width: 100%;
        height: auto;
        display: block;
    }}

    .accueil-hero {{
        position: relative;
        z-index: 2;
        padding: 0 40px;
        margin: 12vh 0 0 8vw;
        max-width: 780px;
        text-align: center;
    }}

    .accueil-hero h1 {{
        color: {PALETTE["orange"]};
        font-weight: 800;
        font-size: clamp(1.7rem, 3.2vw, 2.65rem);
        line-height: 1.3;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        margin: 0;
    }}

    .accueil-hero h1 a {{
        display: none !important;
    }}

    .st-key-accueil_page div[data-testid="stElementContainer"]:has(div[data-testid="stButton"]) {{
        margin: 34px 0 0 8vw !important;
        width: 780px !important;
        max-width: calc(100vw - 16vw) !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }}

    .st-key-accueil_page .stButton {{
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100%;
        flex: none !important;
    }}

    .st-key-accueil_page .stButton > button {{
        flex: none !important;
        width: auto !important;
    }}

    .st-key-accueil_page .stButton > button {{
        background-color: {PALETTE["orange"]} !important;
        color: {PALETTE["navy"]} !important;
        border: none !important;
        border-radius: 50px !important;
        font-weight: 900 !important;
        font-size: 1.35rem !important;
        padding: 16px 44px !important;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.28) !important;
    }}

    .st-key-accueil_page .stButton > button p,
    .st-key-accueil_page .stButton > button div {{
        font-weight: 900 !important;
    }}

    .st-key-accueil_page .stButton > button:hover {{
        background-color: {PALETTE["orange_fonce"]} !important;
        color: {PALETTE["navy"]} !important;
    }}

    .st-key-accueil_page .stButton > button:focus:not(:active) {{
        color: {PALETTE["navy"]} !important;
    }}

    .accueil-train-piste {{
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 110px;
        overflow: hidden;
        z-index: 1;
        pointer-events: none;
    }}

    .accueil-train-piste img {{
        position: absolute;
        top: 50%;
        left: 0;
        height: 60px;
        width: auto;
        transform: translate(-100%, -50%);
        animation: accueil-glissement-train 12s linear infinite;
        will-change: transform;
    }}

    @keyframes accueil-glissement-train {{
        0% {{
            transform: translate(-100%, -50%);
        }}
        100% {{
            transform: translate(110vw, -50%);
        }}
    }}

    @media (prefers-reduced-motion: reduce) {{
        .accueil-train-piste img {{
            animation: none;
            transform: translate(0, -50%);
        }}
    }}

    @media (max-width: 900px) {{
        .accueil-pda {{
            width: 150px;
            top: 18px;
            right: 30px;
        }}
        .accueil-hero {{
            padding: 0 24px;
            margin: 20vh 0 0 5vw;
            max-width: 92%;
        }}
        .accueil-topbar {{
            padding-left: 32px;
        }}
        .st-key-accueil_page div[data-testid="stElementContainer"]:has(div[data-testid="stButton"]) {{
            margin-left: 5vw !important;
            width: 90vw !important;
            max-width: 90vw !important;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(key="accueil_page"):
    st.markdown(
        f"""
        <div class="accueil-topbar">
            <img src="data:image/png;base64,{logo_oncf_b64}" alt="ONCF" />
        </div>
        <div class="accueil-pda">
            <img src="data:image/png;base64,{logo_pda_b64}" alt="PDA" />
        </div>
        <div class="accueil-hero">
            <h1>Plateforme de prédiction de performance commerciale pour PDA</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Accédez au dashboard", key="bouton_accueil_dashboard"):
        st.switch_page("pages/ventes/dashboard_ventes.py")

    st.markdown(
        f"""
        <div class="accueil-train-piste">
            <img src="data:image/png;base64,{logo_train_b64}" alt="Train ONCF" />
        </div>
        """,
        unsafe_allow_html=True,
    )
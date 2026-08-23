import streamlit as st

from config.chatbot import (
    CATEGORIES,
    EXEMPLES_QUESTIONS,
    GLOSSAIRE,
    HORIZONS_DEDIES_CHATBOT,
    HORIZONS_RECURSIFS_CHATBOT,
    LIBELLES_HORIZON,
    MODELES_HORIZON_DEDIE_CHATBOT,
    ORDRE_CATEGORIES,
    SUGGESTIONS_CONTEXTUELLES,
)
from config.modeles import MODELES
from utils.style import PALETTE, entete

entete("Guide du chatbot", "Comment poser vos questions et ce que vous pouvez en attendre")


def _titre_section(texte):
    st.markdown(
        f"<div style='border-left:4px solid {PALETTE['orange']}; padding:2px 0 2px 12px; margin:14px 0 8px 0;'>"
        f"<span style='font-size:1.05rem; font-weight:700; color:{PALETTE['navy']};'>{texte}</span></div>",
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
    div[data-baseweb="tab-list"] button[aria-selected="true"] {
        border-bottom-color: %s !important;
    }
    div[data-baseweb="tab-list"] button[aria-selected="true"] p {
        color: %s !important;
        font-weight: 700 !important;
    }
    </style>
    """ % (PALETTE["orange"], PALETTE["orange_fonce"]),
    unsafe_allow_html=True,
)

st.markdown(
    "Le chatbot fonctionne de deux façons : le **parcours guidé** (choix d'une catégorie, puis d'un modèle "
    "et des filtres disponibles pour cette catégorie — liaison, période, horizon ou heure) ou le "
    "**texte libre**, sans syntaxe imposée. Ce guide détaille, catégorie par catégorie, les questions "
    "possibles et la réponse à en attendre."
)

onglets = st.tabs([CATEGORIES[cle_categorie]["libelle"] for cle_categorie in ORDRE_CATEGORIES])

for onglet, cle_categorie in zip(onglets, ORDRE_CATEGORIES):
    with onglet:
        info_categorie = CATEGORIES[cle_categorie]

        if info_categorie["necessite_modele"]:
            st.caption("Disponible pour les 7 modèles : " + ", ".join(info["libelle_court"] for info in MODELES.values()))

        filtres = []
        if info_categorie["necessite_liaison"]:
            filtres.append("liaison (toutes les liaisons ou une liaison précise)")
        if info_categorie["necessite_periode"]:
            filtres.append("période (toutes les dates, cette semaine, 2 dernières semaines, ce mois ou une date précise)")
        if info_categorie.get("necessite_horizon"):
            filtres.append("horizon de prédiction (J+1 à J+6 pour tous les modèles, J+7/J+15/J+30 pour Billets vendus et Billets contrôlés)")
        if cle_categorie in ("predictions", "historique"):
            filtres.append("heure précise (modèles à granularité horaire : Billets vendus, Billets contrôlés)")
        if filtres:
            st.caption("Filtres disponibles : " + " et ".join(filtres))

        if cle_categorie == "rapports":
            st.caption(
                "Deux actions disponibles depuis le parcours guidé : « Voir les rapports disponibles » "
                "(liste des PDF déjà générés) et « Générer un nouveau rapport » (génération immédiate, "
                "avec bouton de téléchargement dans la réponse)."
            )

        st.markdown("**Exemples de questions et réponses attendues**")
        for question, reponse_attendue in EXEMPLES_QUESTIONS.get(cle_categorie, []):
            with st.container(border=True):
                st.markdown(
                    f"<span style='color:{PALETTE['orange_fonce']}; font-weight:600;'>« {question} »</span>",
                    unsafe_allow_html=True,
                )
                st.caption(reponse_attendue)

        propositions = SUGGESTIONS_CONTEXTUELLES.get(cle_categorie)
        if propositions:
            st.caption("Sujets liés proposés après une réponse : " + ", ".join(CATEGORIES[cle]["libelle"] for cle in propositions))

st.markdown("---")
_titre_section("Glossaire métier")

st.markdown("**Horizons de prédiction (J+N)**")
libelles_modeles_dedies = ", ".join(MODELES[cle]["libelle_court"] for cle in MODELES_HORIZON_DEDIE_CHATBOT)
with st.container(border=True):
    st.markdown(
        f"- **J+1 à J+6** : calculés de façon récursive à partir du modèle standard, disponibles pour "
        f"les **7 modèles** de la plateforme (performance, anomalies, explicabilité et comparaisons "
        f"restent celles du modèle standard J+1 ; seules les prédictions varient selon l'horizon).\n"
        f"- **J+7, J+15, J+30** : modèles dédiés, entraînés spécifiquement pour chacun de ces horizons, "
        f"disponibles uniquement pour **{libelles_modeles_dedies}**. Pour ces deux modèles, la performance, "
        f"les anomalies, l'explicabilité et les comparaisons sont aussi disponibles à ces horizons.\n"
        f"- Pour préciser un horizon en texte libre : « **J+7** », « **à horizon 15 jours** », "
        f"« **dans 30 jours** », « **à une semaine** »… Sans précision, la réponse porte sur J+1 (modèle standard)."
    )
    st.caption(
        "Horizons récursifs : " + ", ".join(LIBELLES_HORIZON[h] for h in HORIZONS_RECURSIFS_CHATBOT)
        + " — Horizons dédiés : " + ", ".join(LIBELLES_HORIZON[h] for h in HORIZONS_DEDIES_CHATBOT)
    )

st.markdown("<div style='height: 6px'></div>", unsafe_allow_html=True)
for terme, definition in GLOSSAIRE.items():
    st.markdown(f"- **{terme}** : {definition}")
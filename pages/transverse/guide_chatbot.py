import streamlit as st

from config.chatbot import CATEGORIES, EXEMPLES_QUESTIONS, GLOSSAIRE, ORDRE_CATEGORIES, SUGGESTIONS_CONTEXTUELLES
from config.modeles import MODELES
from utils.style import entete

entete("Guide du chatbot", "Comment poser vos questions et ce que vous pouvez en attendre")

st.markdown(
    "Le chatbot fonctionne de deux façons : le **parcours guidé** (choix d'une catégorie, puis d'un modèle, "
    "d'une liaison et d'une période) ou le **texte libre**, sans syntaxe imposée. "
    "Ce guide détaille, catégorie par catégorie, les questions possibles et la réponse à en attendre."
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
            filtres.append("période (cette semaine, 2 dernières semaines, ce mois ou une date précise)")
        if filtres:
            st.caption("Filtres disponibles : " + " et ".join(filtres))

        st.markdown("**Exemples de questions et réponses attendues**")
        for question, reponse_attendue in EXEMPLES_QUESTIONS.get(cle_categorie, []):
            with st.container(border=True):
                st.markdown(f"« {question} »")
                st.caption(reponse_attendue)

        propositions = SUGGESTIONS_CONTEXTUELLES.get(cle_categorie)
        if propositions:
            st.caption("Sujets liés proposés après une réponse : " + ", ".join(CATEGORIES[cle]["libelle"] for cle in propositions))

st.markdown("---")
st.markdown("**Glossaire métier**")
for terme, definition in GLOSSAIRE.items():
    st.markdown(f"- **{terme}** : {definition}")
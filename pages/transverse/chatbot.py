import streamlit as st

from config.modeles import MODELES
from utils.chargement import liste_liaisons
from utils.intentions import QUESTIONS_SUGGEREES, repondre
from utils.style import entete

entete("Chatbot", "Posez vos questions sur les ventes, les contrôles ou la fraude")

liaisons_connues = set()
for cle_modele in MODELES:
    liaisons_connues.update(liste_liaisons(cle_modele))

if "historique_chat" not in st.session_state:
    st.session_state["historique_chat"] = []
if "message_en_attente" not in st.session_state:
    st.session_state["message_en_attente"] = None


def _afficher_reponse(reponse):
    if isinstance(reponse, str):
        st.write(reponse)
        return
    st.write(reponse["texte"])
    if reponse.get("metriques"):
        colonnes = st.columns(len(reponse["metriques"]))
        for colonne, (libelle, valeur) in zip(colonnes, reponse["metriques"].items()):
            with colonne:
                st.metric(libelle, valeur)
    if reponse.get("tableau") is not None and not reponse["tableau"].empty:
        st.dataframe(reponse["tableau"], use_container_width=True, hide_index=True)


for role, contenu in st.session_state["historique_chat"]:
    with st.chat_message(role):
        _afficher_reponse(contenu)

if not st.session_state["historique_chat"]:
    st.markdown("**Questions fréquentes**")
    colonnes = st.columns(len(QUESTIONS_SUGGEREES))
    for colonne, question in zip(colonnes, QUESTIONS_SUGGEREES):
        with colonne:
            if st.button(question, use_container_width=True, key=f"suggestion_{question}"):
                st.session_state["message_en_attente"] = question

message = st.chat_input("Posez une question sur les ventes, les contrôles ou la fraude")
if st.session_state["message_en_attente"]:
    message = st.session_state["message_en_attente"]
    st.session_state["message_en_attente"] = None

if message:
    st.session_state["historique_chat"].append(("user", message))
    with st.chat_message("user"):
        st.write(message)

    reponse = repondre(message, liaisons_connues)
    st.session_state["historique_chat"].append(("assistant", reponse))
    with st.chat_message("assistant"):
        _afficher_reponse(reponse)
    st.rerun()
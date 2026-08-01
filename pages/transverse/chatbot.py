import streamlit as st

from config.modeles import MODELES
from utils.chargement import liste_liaisons
from utils.intentions import repondre
from utils.style import entete

entete("Chatbot", "Assistant basé sur des règles pour interroger les données déjà chargées dans la plateforme")

liaisons_connues = set()
for cle_modele in MODELES:
    liaisons_connues.update(liste_liaisons(cle_modele))

if "historique_chat" not in st.session_state:
    st.session_state["historique_chat"] = []

for role, contenu in st.session_state["historique_chat"]:
    with st.chat_message(role):
        st.write(contenu)

message = st.chat_input("Posez une question sur les ventes, les contrôles ou la fraude")

if message:
    st.session_state["historique_chat"].append(("user", message))
    with st.chat_message("user"):
        st.write(message)

    reponse = repondre(message, liaisons_connues)
    st.session_state["historique_chat"].append(("assistant", reponse))
    with st.chat_message("assistant"):
        st.write(reponse)

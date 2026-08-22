from datetime import datetime, timedelta

import streamlit as st

from config.chatbot import (
    CATEGORIES,
    OPTION_LIAISON_PRECISE,
    OPTION_TOUTES_LIAISONS_CHATBOT,
    OPTIONS_PERIODE,
    ORDRE_CATEGORIES,
    SUGGESTIONS_CONTEXTUELLES,
)
from config.modeles import MODELES
from utils.chargement import liste_liaisons
from utils.chatbot import contexte as module_contexte
from utils.chatbot import moteur, reponses
from utils.liaisons import formateur_selectbox_liaison
from utils.style import entete

entete("Chatbot", "Posez vos questions sur toutes les données de la plateforme")

st.page_link("pages/transverse/guide_chatbot.py", label="Consulter le guide du chatbot", icon=":material/menu_book:")

liaisons_par_modele = {cle_modele: liste_liaisons(cle_modele) for cle_modele in MODELES}
liaisons_connues = set()
for liaisons in liaisons_par_modele.values():
    liaisons_connues.update(liaisons)

if "chat_historique" not in st.session_state:
    st.session_state["chat_historique"] = []
if "chat_navigation" not in st.session_state:
    st.session_state["chat_navigation"] = {"categorie": None, "modele": None}

module_contexte.obtenir_contexte(st.session_state)


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

    if reponse.get("figure") is not None:
        st.plotly_chart(reponse["figure"], use_container_width=True)

    if reponse.get("figure_secondaire") is not None:
        st.plotly_chart(reponse["figure_secondaire"], use_container_width=True)

    if reponse.get("tableau") is not None and not reponse["tableau"].empty:
        st.dataframe(reponse["tableau"], use_container_width=True, hide_index=True)

    if reponse.get("fichier_telechargement"):
        with open(reponse["fichier_telechargement"], "rb") as fichier:
            st.download_button(
                "Télécharger le rapport",
                data=fichier.read(),
                file_name=reponse["fichier_telechargement"].split("/")[-1],
                mime="application/pdf",
                key=f"telechargement_{len(st.session_state['chat_historique'])}",
            )


def _ajouter_message(role, contenu):
    st.session_state["chat_historique"].append((role, contenu))


def _traiter_categorie_sans_modele(cle_categorie):
    if cle_categorie == "pipeline":
        return reponses.reponse_pipeline(), "Quel est le dernier traitement du pipeline ?"
    return reponses.reponse_liste_rapports(), "Quels rapports ont déjà été générés ?"


def _traiter_selection(cle_categorie, cle_modele, liaison, borne_debut, borne_fin, sous_type):
    if cle_categorie == "performance":
        return reponses.reponse_performance(cle_modele)
    if cle_categorie == "anomalies":
        return reponses.reponse_anomalies(cle_modele, liaison=liaison, borne_debut=borne_debut, borne_fin=borne_fin)
    if cle_categorie == "predictions":
        return reponses.reponse_predictions(cle_modele, liaison=liaison, borne_debut=borne_debut, borne_fin=borne_fin)
    if cle_categorie == "explicabilite":
        return reponses.reponse_explicabilite(cle_modele)
    if cle_categorie == "comparaison":
        if sous_type == "saisonnalite":
            return reponses.reponse_saisonnalite(cle_modele, liaison)
        if sous_type == "calendrier":
            return reponses.reponse_calendrier(cle_modele)
        return reponses.reponse_comparaison(cle_modele, liaison=liaison)
    return reponses.reponse_repli()


def _libelle_question(cle_categorie, cle_modele, liaison, periode_libelle):
    libelle_modele = MODELES[cle_modele]["libelle"] if cle_modele else ""
    question = f"{CATEGORIES[cle_categorie]['libelle']} — {libelle_modele}" if libelle_modele else CATEGORIES[cle_categorie]["libelle"]
    if liaison:
        question += f" — liaison {liaison}"
    if periode_libelle:
        question += f" — {periode_libelle}"
    return question


for role, contenu in st.session_state["chat_historique"]:
    with st.chat_message(role):
        _afficher_reponse(contenu)

st.markdown("<div style='height: 4px'></div>", unsafe_allow_html=True)

with st.container(border=True, key="parcours_guide"):
    st.markdown("**Parcours guidé**")
    navigation = st.session_state["chat_navigation"]

    colonnes_categories = st.columns(len(ORDRE_CATEGORIES))
    for colonne, cle_categorie in zip(colonnes_categories, ORDRE_CATEGORIES):
        with colonne:
            actif = navigation["categorie"] == cle_categorie
            if st.button(
                CATEGORIES[cle_categorie]["libelle"], use_container_width=True,
                key=f"categorie_{cle_categorie}", type="primary" if actif else "secondary",
            ):
                st.session_state["chat_navigation"] = {"categorie": cle_categorie, "modele": None}
                st.rerun()

    cle_categorie = navigation["categorie"]

    if cle_categorie:
        info_categorie = CATEGORIES[cle_categorie]

        if not info_categorie["necessite_modele"]:
            reponse_prete, libelle_question = _traiter_categorie_sans_modele(cle_categorie)
            if st.button("Poser cette question", key=f"poser_{cle_categorie}"):
                reponse_prete["categorie"] = cle_categorie
                _ajouter_message("user", libelle_question)
                _ajouter_message("assistant", reponse_prete)
                module_contexte.obtenir_contexte(st.session_state)
                st.session_state["chat_navigation"] = {"categorie": None, "modele": None}
                st.rerun()
        else:
            cles_modeles = list(MODELES.keys())
            colonnes_modeles = st.columns(len(cles_modeles))
            for colonne, cle_modele in zip(colonnes_modeles, cles_modeles):
                with colonne:
                    actif = navigation.get("modele") == cle_modele
                    if st.button(
                        MODELES[cle_modele]["libelle_court"], use_container_width=True,
                        key=f"modele_{cle_categorie}_{cle_modele}", type="primary" if actif else "secondary",
                    ):
                        st.session_state["chat_navigation"]["modele"] = cle_modele
                        st.rerun()

            cle_modele = navigation.get("modele")

            if cle_modele:
                liaison = None
                borne_debut = borne_fin = None
                periode_libelle = None
                sous_type = "comparaison"

                if info_categorie["necessite_liaison"]:
                    choix_liaison = st.radio(
                        "Liaison", [OPTION_TOUTES_LIAISONS_CHATBOT, OPTION_LIAISON_PRECISE],
                        key=f"choix_liaison_{cle_categorie}_{cle_modele}", horizontal=True,
                    )
                    if choix_liaison == OPTION_LIAISON_PRECISE:
                        liaisons_disponibles = liaisons_par_modele.get(cle_modele, [])
                        if liaisons_disponibles:
                            liaison = st.selectbox(
                                "Liaison précise", liaisons_disponibles,
                                key=f"liaison_precise_{cle_categorie}_{cle_modele}",
                                format_func=formateur_selectbox_liaison(),
                            )
                        else:
                            st.info("Aucune liaison disponible pour ce modèle.")

                if cle_categorie == "comparaison":
                    sous_type = st.radio(
                        "Type d'analyse", ["comparaison", "saisonnalite", "calendrier"],
                        format_func=lambda valeur: {
                            "comparaison": "Comparaison inter-années",
                            "saisonnalite": "Saisonnalité (nécessite une liaison)",
                            "calendrier": "Calendrier des écarts",
                        }[valeur],
                        key=f"sous_type_{cle_categorie}_{cle_modele}", horizontal=True,
                    )

                if info_categorie["necessite_periode"]:
                    choix_periode = st.radio(
                        "Période", OPTIONS_PERIODE,
                        key=f"choix_periode_{cle_categorie}_{cle_modele}", horizontal=True,
                    )
                    if choix_periode == "Date précise":
                        date_choisie = st.date_input("Date", key=f"date_precise_{cle_categorie}_{cle_modele}")
                        borne_debut = borne_fin = date_choisie
                        periode_libelle = date_choisie.strftime("%d/%m/%Y")
                    else:
                        aujourd_hui = datetime.now().date()
                        jours = {"Cette semaine": 7, "2 dernières semaines": 14, "Ce mois": 30}[choix_periode]
                        borne_debut = aujourd_hui - timedelta(days=jours)
                        borne_fin = aujourd_hui
                        periode_libelle = choix_periode

                if st.button("Poser cette question", key=f"poser_{cle_categorie}_{cle_modele}"):
                    reponse_prete = _traiter_selection(cle_categorie, cle_modele, liaison, borne_debut, borne_fin, sous_type)
                    reponse_prete["categorie"] = cle_categorie
                    libelle_question = _libelle_question(cle_categorie, cle_modele, liaison, periode_libelle)
                    _ajouter_message("user", libelle_question)
                    _ajouter_message("assistant", reponse_prete)
                    module_contexte.mettre_a_jour_contexte(st.session_state, cle_modele=cle_modele, liaison=liaison)
                    st.session_state["chat_navigation"] = {"categorie": None, "modele": None}
                    st.rerun()

if st.session_state["chat_historique"] and st.session_state["chat_navigation"]["categorie"] is None:
    dernier_role, dernier_contenu = st.session_state["chat_historique"][-1]
    if dernier_role == "assistant" and isinstance(dernier_contenu, dict):
        derniere_categorie = dernier_contenu.get("categorie")
        propositions = SUGGESTIONS_CONTEXTUELLES.get(derniere_categorie)
        if propositions:
            st.markdown("**Suggestions**")
            colonnes_suggestions = st.columns(len(propositions))
            for colonne, cle_suggestion in zip(colonnes_suggestions, propositions):
                with colonne:
                    if st.button(
                        CATEGORIES[cle_suggestion]["libelle"], use_container_width=True,
                        key=f"suggestion_{cle_suggestion}_{len(st.session_state['chat_historique'])}",
                    ):
                        st.session_state["chat_navigation"] = {"categorie": cle_suggestion, "modele": None}
                        st.rerun()

message = st.chat_input("Posez une question libre sur les ventes, les contrôles ou la fraude")
if message:
    _ajouter_message("user", message)
    with st.chat_message("user"):
        st.write(message)

    reponse = moteur.repondre_texte_libre(message, st.session_state, liaisons_connues)
    _ajouter_message("assistant", reponse)
    with st.chat_message("assistant"):
        _afficher_reponse(reponse)
    st.rerun()
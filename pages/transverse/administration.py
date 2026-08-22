import time

import requests
import streamlit as st

from config.modeles import MODELES, MODELES_HORIZON_DEDIE, HORIZONS_DEDIES
from utils.chargement import charger_log_execution, dernier_log_execution

URL_API = "http://localhost:8000"

DELAI_MAXIMUM = 5400
INTERVALLE = 3


def _attendre_resultat(id_declenchement, nom_journal_direct):
    zone_log = st.empty()
    resultat_final = None
    temps_ecoule = 0

    while temps_ecoule < DELAI_MAXIMUM:
        time.sleep(INTERVALLE)
        temps_ecoule += INTERVALLE

        try:
            reponse_log = requests.get(f"{URL_API}/journal-direct/{nom_journal_direct}", timeout=10)
            contenu_log = reponse_log.json().get("contenu", "")
        except requests.exceptions.RequestException:
            contenu_log = ""
        if contenu_log:
            zone_log.code(contenu_log, language="text")

        try:
            reponse = requests.get(f"{URL_API}/etat-pipeline", timeout=10)
            journal = reponse.json()
        except requests.exceptions.RequestException:
            continue

        nouvelles_entrees = [
            entree for entree in journal
            if entree.get("id_declenchement") == id_declenchement
            and entree.get("statut") != "en_cours"
        ]

        if nouvelles_entrees:
            resultat_final = nouvelles_entrees[-1]
            zone_log.empty()
            break

    return resultat_final


st.title("Administration")

try:
    reponse_sante = requests.get(f"{URL_API}/sante", timeout=3)
    api_active = reponse_sante.status_code == 200
except requests.exceptions.RequestException:
    api_active = False

if api_active:
    st.success("API en ligne")
else:
    st.error("API hors ligne — lance scripts/lancer_api.sh")

colonne_soustitre_depot, colonne_bouton_actualiser = st.columns([5, 1], vertical_alignment="bottom")
with colonne_soustitre_depot:
    st.subheader("Dernier dépôt de données")
with colonne_bouton_actualiser:
    if st.button("Actualiser", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

dernier = dernier_log_execution()
if dernier is None:
    st.info("Aucun dépôt enregistré")
else:
    with st.container(key="carte_dernier_depot"):
        colonne1, colonne2, colonne3 = st.columns(3)
        colonne1.metric("Horodatage", dernier.get("horodatage", "—"))
        colonne2.metric("Statut", dernier.get("statut", "—"))
        colonne3.metric("Date traitée", dernier.get("date_traitee", "—"))

if st.button("Forcer le traitement"):
    try:
        reponse_declenchement = requests.post(f"{URL_API}/traiter-quotidien", timeout=10)
    except requests.exceptions.RequestException as exception:
        st.session_state["message_traitement"] = {
            "messages": [("error", f"Impossible de declencher le traitement : {exception}")], "json": None,
        }
    else:
        if reponse_declenchement.status_code == 409:
            st.session_state["message_traitement"] = {
                "messages": [("warning", "Un traitement est deja en cours. Attends qu'il se termine avant d'en relancer un.")],
                "json": None,
            }
        elif reponse_declenchement.status_code != 200:
            st.session_state["message_traitement"] = {
                "messages": [("error", f"Le declenchement a echoue : {reponse_declenchement.text}")], "json": None,
            }
        else:
            st.session_state["traitement_en_cours"] = reponse_declenchement.json()["id_declenchement"]
    st.rerun()

if "traitement_en_cours" in st.session_state:
    id_declenchement = st.session_state["traitement_en_cours"]
    with st.spinner("Traitement en cours..."):
        resultat_final = _attendre_resultat(id_declenchement, "traitement")
    del st.session_state["traitement_en_cours"]

    if resultat_final is None:
        st.session_state["message_traitement"] = {
            "messages": [("warning", "Le suivi en direct a expire, mais le traitement continue en arriere-plan et se terminera normalement. Recharge cette page dans quelques minutes pour voir le resultat final.")],
            "json": None,
        }
    elif resultat_final["statut"] == "erreur":
        st.session_state["message_traitement"] = {
            "messages": [("error", f"Le traitement a echoue : {resultat_final.get('erreur')}")], "json": None,
        }
    else:
        st.cache_data.clear()
        messages = [("success", "Traitement termine. Les pages Nouvelles Predictions et Dashboard affichent maintenant les donnees a jour.")]
        if resultat_final.get("alerte_continuite"):
            messages.append(("warning", resultat_final["alerte_continuite"]))
        st.session_state["message_traitement"] = {"messages": messages, "json": resultat_final}
    st.rerun()

if "message_traitement" in st.session_state:
    info_message = st.session_state.pop("message_traitement")
    for type_message, texte_message in info_message["messages"]:
        getattr(st, type_message)(texte_message)
    if info_message["json"] is not None:
        st.json(info_message["json"])

st.subheader("État des réentraînements")
journal = charger_log_execution()
entrees_reentrainement = [entree for entree in journal if entree.get("type") == "reentrainement"]

lignes = []
for cle_modele, info in MODELES.items():
    entrees_modele = [
        entree for entree in entrees_reentrainement
        if entree.get("cle_modele") == cle_modele and entree.get("horizon") is None
    ]
    derniere = entrees_modele[-1] if entrees_modele else None
    lignes.append({
        "Modèle": info["libelle_court"],
        "Horizon": "J+1",
        "Dernier réentraînement": derniere.get("horodatage") if derniere else "jamais",
        "Statut": derniere.get("statut") if derniere else "—",
        "RMSE avant": (derniere.get("metriques_avant") or {}).get("RMSE") if derniere else None,
        "RMSE après": (derniere.get("metriques_apres") or {}).get("RMSE") if derniere else None,
    })

    if cle_modele in MODELES_HORIZON_DEDIE:
        for horizon in HORIZONS_DEDIES:
            entrees_horizon = [
                entree for entree in entrees_reentrainement
                if entree.get("cle_modele") == cle_modele and entree.get("horizon") == horizon
            ]
            derniere_horizon = entrees_horizon[-1] if entrees_horizon else None
            lignes.append({
                "Modèle": info["libelle_court"],
                "Horizon": f"J+{horizon}",
                "Dernier réentraînement": derniere_horizon.get("horodatage") if derniere_horizon else "jamais",
                "Statut": derniere_horizon.get("statut") if derniere_horizon else "—",
                "RMSE avant": (derniere_horizon.get("metriques_avant") or {}).get("RMSE") if derniere_horizon else None,
                "RMSE après": (derniere_horizon.get("metriques_apres") or {}).get("RMSE") if derniere_horizon else None,
            })

horizons_presents = sorted({ligne["Horizon"] for ligne in lignes}, key=lambda texte: int(texte[2:]))
filtre_horizon = st.radio(
    "Filtrer par horizon", options=["Tous"] + horizons_presents, horizontal=True, key="filtre_horizon_administration",
)
lignes_affichees = lignes if filtre_horizon == "Tous" else [ligne for ligne in lignes if ligne["Horizon"] == filtre_horizon]

st.dataframe(lignes_affichees, use_container_width=True)

colonne_selection_modele, colonne_selection_horizon, colonne_bouton = st.columns([2, 1, 1], vertical_alignment="bottom")

cle_choisie = colonne_selection_modele.selectbox(
    "Modèle à réentraîner", options=list(MODELES.keys()),
    format_func=lambda cle: MODELES[cle]["libelle_court"],
    key="choix_modele_reentrainement_administration",
)

if cle_choisie in MODELES_HORIZON_DEDIE:
    options_horizon_reentrainement = [None] + list(HORIZONS_DEDIES)
    horizon_choisi = colonne_selection_horizon.selectbox(
        "Horizon", options=options_horizon_reentrainement,
        format_func=lambda horizon: "J+1" if horizon is None else f"J+{horizon}",
        key=f"choix_horizon_reentrainement_administration_{cle_choisie}",
    )
else:
    horizon_choisi = None
    with colonne_selection_horizon:
        st.text_input("Horizon", value="J+1", disabled=True, key=f"horizon_fixe_administration_{cle_choisie}")

if colonne_bouton.button("Réentraîner maintenant", disabled=not api_active, use_container_width=True):
    parametres = {"horizon": horizon_choisi} if horizon_choisi is not None else {}
    nom_journal_direct = f"reentrainement_{cle_choisie}" if horizon_choisi is None else f"reentrainement_{cle_choisie}_h{horizon_choisi}"
    try:
        reponse_declenchement = requests.post(f"{URL_API}/reentrainer/{cle_choisie}", params=parametres, timeout=10)
    except requests.exceptions.RequestException as exception:
        st.session_state["message_reentrainement"] = {
            "messages": [("error", f"Impossible de declencher le reentrainement : {exception}")], "json": None,
        }
    else:
        if reponse_declenchement.status_code == 409:
            st.session_state["message_reentrainement"] = {
                "messages": [("warning", "Un reentrainement est deja en cours pour ce modele/horizon. Attends qu'il se termine avant d'en relancer un.")],
                "json": None,
            }
        elif reponse_declenchement.status_code != 200:
            st.session_state["message_reentrainement"] = {
                "messages": [("error", f"Le declenchement a echoue : {reponse_declenchement.text}")], "json": None,
            }
        else:
            st.session_state["reentrainement_en_cours"] = {
                "id_declenchement": reponse_declenchement.json()["id_declenchement"],
                "nom_journal_direct": nom_journal_direct,
            }
    st.rerun()

if "reentrainement_en_cours" in st.session_state:
    job = st.session_state["reentrainement_en_cours"]
    with st.spinner("Réentraînement en cours"):
        resultat_final = _attendre_resultat(job["id_declenchement"], job["nom_journal_direct"])
    del st.session_state["reentrainement_en_cours"]

    if resultat_final is None:
        st.session_state["message_reentrainement"] = {
            "messages": [("warning", "Le suivi en direct a expire, mais le reentrainement continue en arriere-plan et se terminera normalement. Recharge cette page dans quelques minutes pour voir le tableau ci-dessus mis a jour.")],
            "json": None,
        }
    elif resultat_final["statut"] in ("erreur", "echec"):
        st.session_state["message_reentrainement"] = {
            "messages": [("error", f"Le reentrainement a echoue : {resultat_final.get('erreur')}")], "json": None,
        }
    elif resultat_final["statut"] == "rejete":
        st.session_state["message_reentrainement"] = {
            "messages": [("warning", "Nouveau modele rejete (regression de performance). L'ancien modele reste en service.")],
            "json": resultat_final,
        }
    else:
        st.cache_data.clear()
        st.session_state["message_reentrainement"] = {
            "messages": [("success", "Reentrainement termine et nouveau modele deploye.")], "json": resultat_final,
        }
    st.rerun()

if "message_reentrainement" in st.session_state:
    info_message = st.session_state.pop("message_reentrainement")
    for type_message, texte_message in info_message["messages"]:
        getattr(st, type_message)(texte_message)
    if info_message["json"] is not None:
        st.json(info_message["json"])
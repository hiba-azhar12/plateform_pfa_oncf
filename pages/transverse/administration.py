import time

import requests
import streamlit as st

from config.modeles import MODELES
from utils.chargement import charger_log_execution, dernier_log_execution
from utils.temps import horodatage_maroc

URL_API = "http://localhost:8000"

DELAI_MAXIMUM = 1500
INTERVALLE = 3


def _attendre_resultat(horodatage_avant, nom_journal_direct, reentrainement=False, cle_modele=None):
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

        if reentrainement:
            nouvelles_entrees = [
                entree for entree in journal
                if entree.get("horodatage", "") > horodatage_avant
                and entree.get("statut") != "en_cours"
                and entree.get("type") == "reentrainement"
                and entree.get("cle_modele") == cle_modele
            ]
        else:
            nouvelles_entrees = [
                entree for entree in journal
                if entree.get("horodatage", "") > horodatage_avant
                and entree.get("statut") != "en_cours"
                and entree.get("type") != "reentrainement"
            ]

        if nouvelles_entrees:
            resultat_final = nouvelles_entrees[-1]
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

st.subheader("Dernier dépôt de données")
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
    horodatage_avant = horodatage_maroc()
    try:
        requests.post(f"{URL_API}/traiter-quotidien", timeout=10)
    except requests.exceptions.RequestException as exception:
        st.error(f"Impossible de declencher le traitement : {exception}")
    else:
        with st.spinner("Traitement en cours..."):
            resultat_final = _attendre_resultat(horodatage_avant, "traitement")

        if resultat_final is None:
            st.warning("Le traitement met plus de temps que prevu. Verifie l'onglet etat du pipeline plus tard.")
        elif resultat_final["statut"] == "erreur":
            st.error(f"Le traitement a echoue : {resultat_final.get('erreur')}")
        else:
            st.cache_data.clear()
            st.success("Traitement termine. Les pages Nouvelles Predictions et Dashboard affichent maintenant les donnees a jour.")
            if resultat_final.get("alerte_continuite"):
                st.warning(resultat_final["alerte_continuite"])
            st.json(resultat_final)

st.subheader("État des réentraînements")
journal = charger_log_execution()
entrees_reentrainement = [entree for entree in journal if entree.get("type") == "reentrainement"]

lignes = []
for cle_modele, info in MODELES.items():
    entrees_modele = [entree for entree in entrees_reentrainement if entree.get("cle_modele") == cle_modele]
    derniere = entrees_modele[-1] if entrees_modele else None
    lignes.append({
        "Modèle": info["libelle_court"],
        "Dernier réentraînement": derniere.get("horodatage") if derniere else "jamais",
        "Statut": derniere.get("statut") if derniere else "—",
        "RMSE avant": (derniere.get("metriques_avant") or {}).get("RMSE") if derniere else None,
        "RMSE après": (derniere.get("metriques_apres") or {}).get("RMSE") if derniere else None,
    })

st.dataframe(lignes, use_container_width=True)

colonne_selection, colonne_bouton = st.columns([3, 1])
cle_choisie = colonne_selection.selectbox(
    "Modèle à réentraîner", options=list(MODELES.keys()),
    format_func=lambda cle: MODELES[cle]["libelle_court"],
)
if colonne_bouton.button("Réentraîner maintenant", disabled=not api_active):
    horodatage_avant = horodatage_maroc()
    try:
        requests.post(f"{URL_API}/reentrainer/{cle_choisie}", timeout=10)
    except requests.exceptions.RequestException as exception:
        st.error(f"Impossible de declencher le reentrainement : {exception}")
    else:
        with st.spinner("Réentraînement en cours"):
            resultat_final = _attendre_resultat(
                horodatage_avant, f"reentrainement_{cle_choisie}",
                reentrainement=True, cle_modele=cle_choisie,
            )

        if resultat_final is None:
            st.warning("Le reentrainement met plus de temps que prevu. Verifie le tableau ci-dessus plus tard.")
        elif resultat_final["statut"] in ("erreur", "echec"):
            st.error(f"Le reentrainement a echoue : {resultat_final.get('erreur')}")
        elif resultat_final["statut"] == "rejete":
            st.warning("Nouveau modele rejete (regression de performance). L'ancien modele reste en service.")
            st.json(resultat_final)
        else:
            st.cache_data.clear()
            st.success("Reentrainement termine et nouveau modele deploye.")
            st.json(resultat_final)
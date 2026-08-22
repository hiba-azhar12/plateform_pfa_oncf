import os

import pandas as pd
import streamlit as st

from config.chemins import REFERENTIEL_LIAISONS


@st.cache_data(show_spinner=False)
def _charger_referentiel():
    if not os.path.isfile(REFERENTIEL_LIAISONS):
        return pd.DataFrame(columns=["LiaisonId", "GAredepart", "GareArrivee"])
    referentiel = pd.read_parquet(REFERENTIEL_LIAISONS)
    referentiel["LiaisonId"] = referentiel["LiaisonId"].astype(str)
    referentiel["GAredepart"] = (
        referentiel["GAredepart"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    )
    referentiel["GareArrivee"] = (
        referentiel["GareArrivee"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    )
    return referentiel


@st.cache_data(show_spinner=False)
def _dictionnaire_noms():
    referentiel = _charger_referentiel()
    if referentiel.empty:
        return {}
    noms = referentiel["GAredepart"] + " -> " + referentiel["GareArrivee"]
    return dict(zip(referentiel["LiaisonId"], noms))


def dictionnaire_noms():
    """Retourne le dictionnaire complet {LiaisonId (str) -> nom lisible}, en un seul
    appel a la fonction mise en cache par Streamlit.

    A utiliser pour tout traitement repete (format_func d'un selectbox avec de
    nombreuses options, colonne ajoutee a un tableau de plusieurs lignes, etc.).
    Appeler nom_liaison()/libelle_liaison() dans une boucle Python est tres lent :
    chaque appel a une fonction @st.cache_data coute plusieurs millisecondes
    (verrous internes, hachage des arguments), meme en cas de cache "chaud".
    Sur une liste de ~2000 liaisons cela representait plusieurs secondes,
    recalculees a chaque interaction puisque Streamlit relance tout le script
    a chaque clic. Un dictionnaire Python brut recupere une seule fois, puis
    interroge en boucle localement (dict.get / Series.map), fait la meme chose
    en une fraction de milliseconde."""
    return _dictionnaire_noms()


def nom_liaison(liaison_id):
    """Retourne 'GareDepart -> GareArrivee' si connu, sinon l'identifiant tel quel.
    Pratique pour un affichage ponctuel (une seule liaison). Pour un traitement
    en boucle ou sur toute une colonne, preferer dictionnaire_noms()."""
    identifiant = str(liaison_id)
    return _dictionnaire_noms().get(identifiant, identifiant)


def libelle_liaison(liaison_id):
    """Retourne 'GareDepart -> GareArrivee (id)' si connu, sinon l'identifiant tel quel."""
    identifiant = str(liaison_id)
    nom = nom_liaison(identifiant)
    if nom == identifiant:
        return identifiant
    return f"{nom} ({identifiant})"


def formateur_selectbox_liaison(option_speciale=None):
    """Construit un format_func pour st.selectbox qui affiche le nom de la liaison
    tout en conservant l'identifiant brut comme valeur sous-jacente. Les options
    speciales (ex. 'Toutes les liaisons') sont affichees telles quelles.

    Le dictionnaire est recupere une seule fois ici (hors boucle) : le format_func
    retourne fait uniquement des lookups sur dict Python brut, quel que soit le
    nombre d'options a formater."""
    noms = dictionnaire_noms()

    def _formater(valeur):
        if option_speciale is not None and valeur == option_speciale:
            return valeur
        identifiant = str(valeur)
        nom = noms.get(identifiant)
        if not nom:
            return identifiant
        return f"{nom} ({identifiant})"

    return _formater


def ajouter_colonne_nom_liaison(table, colonne_id="LiaisonId", colonne_nom="Liaison"):
    """Insere une colonne lisible juste apres la colonne d'identifiant, sans la retirer.
    Utilise un seul appel a dictionnaire_noms() puis Series.map (vectorise), au lieu
    d'appeler nom_liaison() une fois par ligne."""
    if table is None or table.empty or colonne_id not in table.columns:
        return table
    noms = dictionnaire_noms()
    table = table.copy()
    identifiants = table[colonne_id].astype(str)
    position = table.columns.get_loc(colonne_id) + 1
    table.insert(position, colonne_nom, identifiants.map(noms).fillna(identifiants))
    return table
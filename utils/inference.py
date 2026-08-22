import gc
import json
import os

import numpy as np
import pandas as pd
import psutil

from config.modeles import (
    LAGS,
    FENETRES_ROLLING,
    MODELES,
    chemin_fichier,
    chemin_modele,
    chemin_fichier_horizon,
    chemin_modele_horizon,
)
from utils.feature_engineering import (
    ajouter_lags_rolling_calendaires,
    calculer_encodage_expanding,
    calculer_features_calendaires,
    calculer_interaction_jour,
    calculer_liaison_frequence,
)

CIBLES_TRAITEMENT = {
    "modele1_ventes": {"completes": [("ventes", "NbBillets")], "exogenes": []},
    "modele3_controles": {"completes": [("controles", "NbControles")], "exogenes": []},
    "modele2_taux_vente_guichet": {"completes": [("ventes", "NbBillets")], "exogenes": [("circulations", "NbCirculations")]},
    "modele5_taux_controle": {"completes": [("controles", "NbControles")], "exogenes": [("circulations", "NbCirculations")]},
    "modele6_taux_fraude": {"completes": [("fraudes", "NbFraudes")], "exogenes": [("controles", "NbControles")]},
    "modele4_part_confort": {"completes": [("ventes", "NbBillets")], "exogenes": []},
    "modele7_part_type": {"completes": [("controles", "NbControles")], "exogenes": []},
}

FENETRE_LAGS_JOURS = 420


def _afficher_ram(etiquette):
    print(f"[RAM] {etiquette} : {round(psutil.Process().memory_info().rss / 1e9, 2)} Go", flush=True)


def _lire_json(chemin):
    if not os.path.isfile(chemin):
        return None
    with open(chemin, "r") as fichier:
        return json.load(fichier)


def _lire_csv(chemin):
    if not os.path.isfile(chemin):
        return pd.DataFrame()
    return pd.read_csv(chemin)


def charger_colonnes_features(cle_modele):
    return _lire_json(chemin_fichier(cle_modele, "colonnes_features")) or []


def charger_encodage(cle_modele):
    encodage = _lire_csv(chemin_fichier(cle_modele, "encodage_liaison"))
    if not encodage.empty and "LiaisonId" in encodage.columns:
        encodage["LiaisonId"] = (
            encodage["LiaisonId"].astype(str).str.replace(r"\.0$", "", regex=True)
        )
    return encodage


def charger_colonnes_features_horizon(cle_modele, horizon):
    return _lire_json(chemin_fichier_horizon(cle_modele, horizon, "colonnes_features")) or []


def charger_encodage_horizon(cle_modele, horizon):
    encodage = _lire_csv(chemin_fichier_horizon(cle_modele, horizon, "encodage_liaison"))
    if not encodage.empty and "LiaisonId" in encodage.columns:
        encodage["LiaisonId"] = (
            encodage["LiaisonId"].astype(str).str.replace(r"\.0$", "", regex=True)
        )
    return encodage


def colonnes_groupe_liaison(cle_modele):
    info = MODELES[cle_modele]
    base = ["LiaisonId", "Heure"] if info["granularite"] == "horaire" else ["LiaisonId"]
    if info["famille"] == "composition":
        base = base + [info["colonne_categorie"]]
    return base


def colonnes_groupe_jour(cle_modele):
    info = MODELES[cle_modele]
    base = ["LiaisonId", "JourSemaine"]
    if info["famille"] == "composition":
        base = base + [info["colonne_categorie"]]
    return base


def generer_lignes_a_predire(cle_modele, date_cible, historique):
    colonnes_cles = colonnes_groupe_liaison(cle_modele)
    combinaisons = historique[colonnes_cles].drop_duplicates().reset_index(drop=True)
    combinaisons["Date"] = pd.Timestamp(date_cible)
    return combinaisons


def preparer_liaison_id_generique(table, format_modele, colonnes_attendues, encodage):
    table = table.copy()
    table["LiaisonId_reel"] = table["LiaisonId"].astype(str)

    if format_modele == "catboost":
        table["LiaisonId"] = table["LiaisonId"].map(str)
        return table, []

    colonne_code = "LiaisonId_code" if "LiaisonId_code" in colonnes_attendues else "LiaisonId"

    if encodage.empty or "LiaisonId" not in encodage.columns:
        codes_factorises, _ = pd.factorize(table["LiaisonId"].astype(str))
        codes = pd.Series(codes_factorises, index=table.index).astype("Int32")
    else:
        mapping = dict(zip(encodage["LiaisonId"].astype(str), encodage["Code"]))
        codes = table["LiaisonId"].astype(str).map(mapping).astype("Int32")

    masque_connu = codes.notna()
    liaisons_inconnues = sorted(table.loc[~masque_connu, "LiaisonId"].astype(str).unique().tolist())

    table = table.loc[masque_connu].copy()
    codes = codes.loc[masque_connu]

    if colonne_code == "LiaisonId_code":
        table["LiaisonId_code"] = codes.astype("int32")
    else:
        table["LiaisonId"] = codes.astype("int32")
    return table, liaisons_inconnues


def preparer_liaison_id(table, cle_modele, encodage, colonnes_attendues):
    info = MODELES[cle_modele]
    return preparer_liaison_id_generique(table, info["format_modele"], colonnes_attendues, encodage)


def construire_features(cle_modele, date_cible, historique):
    info = MODELES[cle_modele]
    traitement = CIBLES_TRAITEMENT[cle_modele]
    groupe_liaison = colonnes_groupe_liaison(cle_modele)
    groupe_jour = colonnes_groupe_jour(cle_modele)

    _afficher_ram(f"{cle_modele} - debut construire_features")

    lignes_base = generer_lignes_a_predire(cle_modele, date_cible, historique)

    frequences = calculer_liaison_frequence(historique, ["LiaisonId"])
    table_frequence = historique[["LiaisonId"]].copy()
    table_frequence["liaison_frequence"] = frequences
    table_frequence = table_frequence.drop_duplicates("LiaisonId")
    lignes_base = lignes_base.merge(table_frequence, on="LiaisonId", how="left")

    toutes_cibles = traitement["completes"] + traitement["exogenes"]
    for _, colonne_valeur in toutes_cibles:
        if colonne_valeur not in lignes_base.columns:
            lignes_base[colonne_valeur] = np.nan

    historique_etendu = pd.concat([historique, lignes_base], ignore_index=True, sort=False)
    historique_etendu = historique_etendu.sort_values(groupe_liaison + ["Date"]).reset_index(drop=True)
    historique_etendu["JourSemaine"] = pd.to_datetime(historique_etendu["Date"]).dt.dayofweek
    _afficher_ram(f"{cle_modele} - apres concat historique complet")

    for nom_suffixe, colonne_valeur in traitement["completes"]:
        historique_etendu[f"liaison_cible_encodage_{nom_suffixe}"] = calculer_encodage_expanding(
            historique_etendu, colonne_valeur, groupe_liaison
        )
        historique_etendu[f"interaction_jour_liaison_{nom_suffixe}"] = calculer_interaction_jour(
            historique_etendu, colonne_valeur, groupe_jour
        )
    _afficher_ram(f"{cle_modele} - apres encodage et interaction (historique complet)")

    date_limite = pd.Timestamp(date_cible) - pd.Timedelta(days=FENETRE_LAGS_JOURS)
    fenetre_recente = historique_etendu[historique_etendu["Date"] >= date_limite].reset_index(drop=True)
    del historique_etendu
    _afficher_ram(f"{cle_modele} - apres restriction fenetre {FENETRE_LAGS_JOURS}j")

    for nom_suffixe, colonne_valeur in toutes_cibles:
        fenetre_recente = ajouter_lags_rolling_calendaires(
            fenetre_recente, colonne_valeur, groupe_liaison, LAGS, FENETRES_ROLLING, nom_suffixe=nom_suffixe
        )
        _afficher_ram(f"{cle_modele} - apres lags_rolling_calendaires {nom_suffixe}")

    masque_nouvelles_lignes = fenetre_recente["Date"] == pd.Timestamp(date_cible)
    table = fenetre_recente[masque_nouvelles_lignes].copy()
    del fenetre_recente

    if "Heure" in table.columns:
        table["Heure"] = table["Heure"].astype(int)

    for nom_suffixe, colonne_valeur in traitement["exogenes"]:
        valeur_proxy = table[f"lag_1_{nom_suffixe}"]
        table[colonne_valeur] = valeur_proxy
        table[f"log_offset_{nom_suffixe}"] = np.log1p(valeur_proxy.clip(lower=0))

    denominateur = info.get("cible_denominateur")
    if denominateur is not None:
        suffixe_denominateur = next(
            (suffixe for suffixe, colonne in traitement["completes"] if colonne == denominateur),
            None,
        )
        if suffixe_denominateur is not None:
            valeur_proxy = table[f"lag_1_{suffixe_denominateur}"]
            table[denominateur] = valeur_proxy
            table[f"log_offset_{suffixe_denominateur}"] = np.log1p(valeur_proxy.clip(lower=0))

    avec_heure = "Heure" in table.columns
    calendaires = calculer_features_calendaires(
        table["Date"], avec_heure=avec_heure, heures=table["Heure"] if avec_heure else None
    )
    colonnes_calendaires_a_ajouter = [c for c in calendaires.columns if c not in ("Date", "Heure")]
    table = table.reset_index(drop=True)
    table[colonnes_calendaires_a_ajouter] = calendaires[colonnes_calendaires_a_ajouter].reset_index(drop=True)

    colonnes_attendues = charger_colonnes_features(cle_modele)
    encodage = charger_encodage(cle_modele)
    table, liaisons_inconnues = preparer_liaison_id(table, cle_modele, encodage, colonnes_attendues)

    colonnes_manquantes = [colonne for colonne in colonnes_attendues if colonne not in table.columns]
    for colonne in colonnes_manquantes:
        table[colonne] = np.nan

    _afficher_ram(f"{cle_modele} - fin construire_features")
    return table, colonnes_attendues, colonnes_manquantes, liaisons_inconnues


def construire_features_horizon_dedie(cle_modele, horizon, historique):
    info = MODELES[cle_modele]
    traitement = CIBLES_TRAITEMENT[cle_modele]
    groupe_liaison = colonnes_groupe_liaison(cle_modele)
    groupe_jour = colonnes_groupe_jour(cle_modele)

    _afficher_ram(f"{cle_modele} h{horizon} - debut construire_features_horizon_dedie")

    date_ancrage = pd.to_datetime(historique["Date"]).max()

    table = historique.sort_values(groupe_liaison + ["Date"]).reset_index(drop=True).copy()
    table["Date"] = pd.to_datetime(table["Date"])
    table["JourSemaine"] = table["Date"].dt.dayofweek
    table["liaison_frequence"] = calculer_liaison_frequence(table, ["LiaisonId"])

    toutes_cibles = traitement["completes"] + traitement["exogenes"]

    for nom_suffixe, colonne_valeur in traitement["completes"]:
        table[f"liaison_cible_encodage_{nom_suffixe}"] = calculer_encodage_expanding(table, colonne_valeur, groupe_liaison)
        table[f"interaction_jour_liaison_{nom_suffixe}"] = calculer_interaction_jour(table, colonne_valeur, groupe_jour)
    _afficher_ram(f"{cle_modele} h{horizon} - apres encodage et interaction")

    date_limite = date_ancrage - pd.Timedelta(days=FENETRE_LAGS_JOURS)
    table = table[table["Date"] >= date_limite].reset_index(drop=True)
    _afficher_ram(f"{cle_modele} h{horizon} - apres restriction fenetre {FENETRE_LAGS_JOURS}j")

    for nom_suffixe, colonne_valeur in toutes_cibles:
        table = ajouter_lags_rolling_calendaires(
            table, colonne_valeur, groupe_liaison, LAGS, FENETRES_ROLLING, nom_suffixe=nom_suffixe
        )
        _afficher_ram(f"{cle_modele} h{horizon} - apres lags_rolling_calendaires {nom_suffixe}")

    table = table[table["Date"] == date_ancrage].copy()

    if "Heure" in table.columns:
        table["Heure"] = table["Heure"].astype(int)

    avec_heure = "Heure" in table.columns
    calendaires = calculer_features_calendaires(
        table["Date"], avec_heure=avec_heure, heures=table["Heure"] if avec_heure else None
    )
    colonnes_calendaires_a_ajouter = [c for c in calendaires.columns if c not in ("Date", "Heure")]
    table = table.reset_index(drop=True)
    table[colonnes_calendaires_a_ajouter] = calendaires[colonnes_calendaires_a_ajouter].reset_index(drop=True)

    colonnes_attendues = charger_colonnes_features_horizon(cle_modele, horizon)
    encodage = charger_encodage_horizon(cle_modele, horizon)
    table, liaisons_inconnues = preparer_liaison_id_generique(table, info["format_modele"], colonnes_attendues, encodage)

    colonnes_manquantes = [colonne for colonne in colonnes_attendues if colonne not in table.columns]
    for colonne in colonnes_manquantes:
        table[colonne] = np.nan

    _afficher_ram(f"{cle_modele} h{horizon} - fin construire_features_horizon_dedie")
    return table, colonnes_attendues, colonnes_manquantes, liaisons_inconnues, date_ancrage


def charger_modele_simple(cle_modele):
    info = MODELES[cle_modele]
    chemin = chemin_modele(cle_modele)
    if info["format_modele"] == "catboost":
        from catboost import CatBoostRegressor
        modele = CatBoostRegressor()
        modele.load_model(chemin)
        return modele
    import lightgbm as lgb
    return lgb.Booster(model_file=chemin)


def charger_modele_horizon(cle_modele, horizon):
    info = MODELES[cle_modele]
    chemin = chemin_modele_horizon(cle_modele, horizon)
    if info["format_modele"] == "catboost":
        from catboost import CatBoostRegressor
        modele = CatBoostRegressor()
        modele.load_model(chemin)
        return modele
    import lightgbm as lgb
    return lgb.Booster(model_file=chemin)


def charger_modeles_categorie(cle_modele):
    info = MODELES[cle_modele]
    mapping = _lire_json(os.path.join(info["dossier"], info["mapping_modeles"])) or {}
    import lightgbm as lgb

    modeles = {}
    for categorie, nom_fichier in mapping.items():
        chemin = os.path.join(info["dossier"], info["dossier_modeles"], nom_fichier)
        modeles[categorie] = lgb.Booster(model_file=chemin)
    return modeles


def predire(cle_modele, table_features, colonnes_attendues):
    info = MODELES[cle_modele]

    if info["multi_categorie"]:
        modeles = charger_modeles_categorie(cle_modele)
        parties = []
        for categorie, modele in modeles.items():
            sous = table_features[table_features[info["colonne_categorie"]].astype(str) == str(categorie)]
            if sous.empty:
                continue
            predictions_brutes = np.clip(modele.predict(sous[colonnes_attendues]), 0, None)
            parties.append(sous.assign(PredictionBrute=predictions_brutes))

        if not parties:
            table_features["Prediction"] = np.nan
            resultat = table_features
        else:
            complet = pd.concat(parties).reset_index(drop=True)
            sommes = complet.groupby(["Date", "LiaisonId"])["PredictionBrute"].transform("sum")
            complet["Prediction"] = np.where(sommes > 0, complet["PredictionBrute"] / sommes, 0.0)
            resultat = complet.drop(columns=["PredictionBrute"])
    else:
        modele = charger_modele_simple(cle_modele)
        predictions = np.clip(modele.predict(table_features[colonnes_attendues]), 0, None)

        if info["famille"] == "taux":
            predictions = np.clip(predictions, 0, 1)

        resultat = table_features.copy()
        resultat["Prediction"] = predictions

    if "LiaisonId_reel" in resultat.columns:
        resultat["LiaisonId"] = resultat["LiaisonId_reel"]
        resultat = resultat.drop(columns=["LiaisonId_reel"])
    if "LiaisonId_code" in resultat.columns:
        resultat = resultat.drop(columns=["LiaisonId_code"])

    return resultat


def predire_nouvelle_date(cle_modele, date_cible, historique):
    table, colonnes_attendues, colonnes_manquantes, liaisons_inconnues = construire_features(cle_modele, date_cible, historique)
    resultat = predire(cle_modele, table, colonnes_attendues)
    resultat["DateCalculPrediction"] = pd.Timestamp.now().normalize()
    return resultat, colonnes_manquantes, liaisons_inconnues


def predire_horizon_dedie(cle_modele, horizon, historique):
    info = MODELES[cle_modele]
    table, colonnes_attendues, colonnes_manquantes, liaisons_inconnues, date_ancrage = construire_features_horizon_dedie(
        cle_modele, horizon, historique
    )

    modele = charger_modele_horizon(cle_modele, horizon)
    predictions = np.clip(modele.predict(table[colonnes_attendues]), 0, None)

    resultat = table.copy()
    resultat["Prediction"] = predictions

    if "LiaisonId_reel" in resultat.columns:
        resultat["LiaisonId"] = resultat["LiaisonId_reel"]
        resultat = resultat.drop(columns=["LiaisonId_reel"])
    if "LiaisonId_code" in resultat.columns:
        resultat = resultat.drop(columns=["LiaisonId_code"])

    resultat["DateAncrage"] = date_ancrage
    resultat["Date"] = date_ancrage + pd.Timedelta(days=horizon)
    resultat["Horizon"] = horizon
    resultat["DateCalculPrediction"] = pd.Timestamp.now().normalize()

    return resultat, colonnes_manquantes, liaisons_inconnues


def _proxy_denominateur(cle_modele, table_predite):
    info = MODELES[cle_modele]
    denominateur = info.get("cible_denominateur")
    if denominateur is not None and denominateur in table_predite.columns:
        return table_predite[denominateur]
    return None


def _volume_total_par_liaison(cle_modele, historique):
    traitement = CIBLES_TRAITEMENT[cle_modele]
    colonne_volume = traitement["completes"][0][1]
    historique = historique.copy()
    historique["Date"] = pd.to_datetime(historique["Date"])
    derniere_date = historique["Date"].max()
    recent = historique[historique["Date"] == derniere_date]
    totaux = recent.groupby(recent["LiaisonId"].astype(str))[colonne_volume].sum()
    return totaux.astype(float).to_dict()


def _valeur_completes_a_injecter(cle_modele, table_predite, proxy_volume_total):
    info = MODELES[cle_modele]

    if info["famille"] == "comptages":
        return table_predite["Prediction"]

    if info["famille"] == "taux":
        proxy = _proxy_denominateur(cle_modele, table_predite)
        if proxy is not None:
            return table_predite["Prediction"] * proxy
        return table_predite["Prediction"]

    if info["famille"] == "composition":
        liaisons = table_predite["LiaisonId"].astype(str)
        totaux = liaisons.map(proxy_volume_total or {}).fillna(0.0)
        return table_predite["Prediction"] * totaux

    return table_predite["Prediction"]


def _construire_ligne_injection(cle_modele, table_predite, valeurs_completes):
    info = MODELES[cle_modele]
    traitement = CIBLES_TRAITEMENT[cle_modele]

    colonnes_cles = ["Date", "LiaisonId"]
    if info["granularite"] == "horaire":
        colonnes_cles.append("Heure")
    if info["famille"] == "composition":
        colonnes_cles.append(info["colonne_categorie"])

    ligne = table_predite[colonnes_cles].copy()
    ligne = ligne.reset_index(drop=True)

    _, colonne_completes_principale = traitement["completes"][0]
    ligne[colonne_completes_principale] = valeurs_completes.reset_index(drop=True).values

    for nom_suffixe, colonne_exogene in traitement["exogenes"]:
        if colonne_exogene in table_predite.columns:
            ligne[colonne_exogene] = table_predite[colonne_exogene].reset_index(drop=True).values

    ligne[info["cible"]] = table_predite["Prediction"].reset_index(drop=True).values

    return ligne


def predire_horizons_recursifs(cle_modele, horizons, historique):
    info = MODELES[cle_modele]
    historique_etendu = historique.copy()
    historique_etendu["Date"] = pd.to_datetime(historique_etendu["Date"])
    date_ancrage = historique_etendu["Date"].max()

    proxy_volume_total = None
    if info["famille"] == "composition":
        proxy_volume_total = _volume_total_par_liaison(cle_modele, historique)

    horizons_tries = sorted(horizons)
    resultats = {}

    for indice, horizon in enumerate(horizons_tries):
        date_cible = date_ancrage + pd.Timedelta(days=horizon)

        resultat, colonnes_manquantes, liaisons_inconnues = predire_nouvelle_date(cle_modele, date_cible, historique_etendu)
        resultat = resultat.copy()
        resultat["DateAncrage"] = date_ancrage
        resultat["Horizon"] = horizon

        resultats[horizon] = (resultat, colonnes_manquantes, liaisons_inconnues)

        if indice < len(horizons_tries) - 1:
            valeurs_completes = _valeur_completes_a_injecter(cle_modele, resultat, proxy_volume_total)
            ligne_injectee = _construire_ligne_injection(cle_modele, resultat, valeurs_completes)
            historique_etendu = pd.concat([historique_etendu, ligne_injectee], ignore_index=True, sort=False)

        gc.collect()
        _afficher_ram(f"{cle_modele} - fin horizon recursif {horizon}")

    return resultats
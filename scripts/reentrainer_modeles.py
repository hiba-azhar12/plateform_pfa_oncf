import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import psutil

from config.chemins import HISTORIQUE, LOG_EXECUTION
from config.modeles import LAGS, FENETRES_ROLLING, MODELES, chemin_fichier, chemin_modele
from utils.feature_engineering import (
    ajouter_lags_rolling_calendaires,
    calculer_encodage_expanding,
    calculer_features_calendaires,
    calculer_interaction_jour,
    calculer_liaison_frequence,
)
from utils.inference import (
    CIBLES_TRAITEMENT,
    charger_modele_simple,
    charger_modeles_categorie,
    colonnes_groupe_jour,
    colonnes_groupe_liaison,
)

TOLERANCE_REGRESSION = 1.1
PART_VALIDATION = 0.15

PARAMETRES_LIGHTGBM_BASE = dict(
    n_estimators=1000, learning_rate=0.05, num_leaves=63, max_depth=8,
    subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
    reg_alpha=0.1, reg_lambda=0.1, random_state=42,
    force_row_wise=True, deterministic=True,
)

PARAMETRES_CATBOOST_BASE = dict(
    iterations=1000, learning_rate=0.05, depth=8, l2_leaf_reg=3.0,
    random_seed=42, early_stopping_rounds=30, verbose=False,
)

SPECIFICATIONS = {
    "modele1_ventes": {"format": "catboost", "loss_function": "RMSE", "taille_max": 5_000_000, "composition": False},
    "modele2_taux_vente_guichet": {"format": "lightgbm", "objectif_lgbm": "tweedie", "params_supplementaires": {"tweedie_variance_power": 1.5}, "taille_max": None, "composition": False},
    "modele3_controles": {"format": "lightgbm", "objectif_lgbm": "tweedie", "params_supplementaires": {"tweedie_variance_power": 1.1}, "taille_max": None, "composition": False},
    "modele4_part_confort": {"format": "lightgbm", "objectif_lgbm": "regression", "params_supplementaires": {}, "taille_max": None, "composition": True},
    "modele5_taux_controle": {"format": "catboost", "loss_function": "Tweedie:variance_power=1.5", "taille_max": None, "composition": False},
    "modele6_taux_fraude": {"format": "lightgbm", "objectif_lgbm": "regression", "params_supplementaires": {}, "taille_max": 3_000_000, "composition": False},
    "modele7_part_type": {"format": "lightgbm", "objectif_lgbm": "regression", "params_supplementaires": {}, "taille_max": None, "composition": True},
}


def _afficher_ram(etiquette):
    print(f"[RAM] {etiquette} : {round(psutil.Process().memory_info().rss / 1e9, 2)} Go", flush=True)


def _chemin_historique(cle_modele):
    return os.path.join(HISTORIQUE, f"{cle_modele}.parquet")


def _cible_composition(cle_modele, table):
    info = MODELES[cle_modele]
    colonne_brute = "NbBillets" if "NbBillets" in table.columns else "NbControles"
    total = table.groupby(["Date", "LiaisonId"])[colonne_brute].transform("sum")
    table[info["cible"]] = table[colonne_brute] / total.replace(0, np.nan)
    return table


def construire_table_entrainement(cle_modele, historique):
    info = MODELES[cle_modele]
    traitement = CIBLES_TRAITEMENT[cle_modele]
    groupe_liaison = colonnes_groupe_liaison(cle_modele)
    groupe_jour = colonnes_groupe_jour(cle_modele)

    _afficher_ram("debut construire_table_entrainement")

    table = historique.sort_values(groupe_liaison + ["Date"]).reset_index(drop=True)
    _afficher_ram("apres sort_values")

    table["JourSemaine"] = pd.to_datetime(table["Date"]).dt.dayofweek
    table["liaison_frequence"] = calculer_liaison_frequence(table, ["LiaisonId"])
    _afficher_ram("apres liaison_frequence")

    toutes_cibles = traitement["completes"] + traitement["exogenes"]
    for nom_suffixe, colonne_valeur in toutes_cibles:
        table = ajouter_lags_rolling_calendaires(table, colonne_valeur, groupe_liaison, LAGS, FENETRES_ROLLING, nom_suffixe=nom_suffixe)
        _afficher_ram(f"apres lags_rolling_calendaires {nom_suffixe}")

    for nom_suffixe, colonne_valeur in traitement["completes"]:
        table[f"liaison_cible_encodage_{nom_suffixe}"] = calculer_encodage_expanding(table, colonne_valeur, groupe_liaison)
        table[f"interaction_jour_liaison_{nom_suffixe}"] = calculer_interaction_jour(table, colonne_valeur, groupe_jour)
    _afficher_ram("apres encodage et interaction")

    for nom_suffixe, colonne_valeur in traitement["exogenes"]:
        table[f"log_offset_{nom_suffixe}"] = np.log1p(table[colonne_valeur].clip(lower=0))

    avec_heure = info["granularite"] == "horaire"
    calendaires = calculer_features_calendaires(
        table["Date"], avec_heure=avec_heure, heures=table["Heure"] if avec_heure else None
    )
    colonnes_calendaires = [c for c in calendaires.columns if c not in ("Date", "Heure")]
    table = table.reset_index(drop=True)
    table[colonnes_calendaires] = calendaires[colonnes_calendaires].reset_index(drop=True)
    _afficher_ram("apres features calendaires")

    denominateur = info.get("cible_denominateur")
    if info["famille"] == "composition":
        table = _cible_composition(cle_modele, table)
    elif denominateur is not None:
        colonne_principale = traitement["completes"][0][1]
        table[info["cible"]] = table[colonne_principale] / table[denominateur].replace(0, np.nan)

    _afficher_ram("fin construire_table_entrainement")
    return table


def _encoder_liaison(cle_modele, table):
    info = MODELES[cle_modele]
    table["LiaisonId"] = table["LiaisonId"].astype(str)

    if info["format_modele"] == "catboost":
        return table, None

    liaisons = sorted(table["LiaisonId"].unique())
    mapping = {liaison: code for code, liaison in enumerate(liaisons)}
    encodage = pd.DataFrame({"LiaisonId": liaisons, "Code": [mapping[l] for l in liaisons]})
    codes = table["LiaisonId"].map(mapping).astype("int32")
    if info["multi_categorie"]:
        table["LiaisonId_code"] = codes
    else:
        table["LiaisonId"] = codes
    return table, encodage


def _dates_coupure(table):
    dates_uniques = sorted(table["Date"].unique())
    indice_coupure = max(1, int(len(dates_uniques) * (1 - PART_VALIDATION)))
    return dates_uniques[indice_coupure]


def _separer_train_validation(table, date_coupure):
    train = table[table["Date"] < date_coupure]
    validation = table[table["Date"] >= date_coupure]
    return train, validation


def _calculer_metriques(y_vrai, y_predit):
    y_vrai = np.asarray(y_vrai, dtype=float)
    y_predit = np.asarray(y_predit, dtype=float)
    erreur = y_vrai - y_predit
    rmse = float(np.sqrt(np.mean(erreur ** 2)))
    mae = float(np.mean(np.abs(erreur)))
    medae = float(np.median(np.abs(erreur)))
    somme_absolue = float(np.sum(np.abs(y_vrai)))
    wmape = float(np.sum(np.abs(erreur)) / somme_absolue) if somme_absolue > 0 else None
    return {"RMSE": rmse, "MAE": mae, "MedAE": medae, "WMAPE": wmape, "NbLignesValidation": int(len(y_vrai))}


def _normaliser_par_groupe(table, valeurs):
    valeurs = np.clip(valeurs, 0, None)
    serie = pd.Series(valeurs, index=table.index)
    sommes = serie.groupby([table["Date"], table["LiaisonId"]], observed=True).transform("sum")
    tailles = serie.groupby([table["Date"], table["LiaisonId"]], observed=True).transform("size")
    part = serie / sommes.replace(0, np.nan)
    part = part.fillna(1.0 / tailles)
    return part.values


def _sous_echantillonner(train, taille_max):
    if taille_max is not None and len(train) > taille_max:
        return train.sample(taille_max, random_state=42)
    return train


def _entrainer_catboost(x_train, y_train, x_valid, y_valid, loss_function):
    from catboost import CatBoostRegressor, Pool
    _afficher_ram("avant Pool train")
    pool_train = Pool(x_train, y_train, cat_features=["LiaisonId"])
    _afficher_ram("apres Pool train")
    pool_valid = Pool(x_valid, y_valid, cat_features=["LiaisonId"])
    _afficher_ram("apres Pool valid")
    modele = CatBoostRegressor(loss_function=loss_function, **PARAMETRES_CATBOOST_BASE)
    modele.fit(pool_train, eval_set=pool_valid, use_best_model=True)
    _afficher_ram("apres fit catboost")
    return modele


def _entrainer_lightgbm(x_train, y_train, x_valid, y_valid, objectif, params_supplementaires):
    import lightgbm as lgb
    parametres = dict(PARAMETRES_LIGHTGBM_BASE)
    parametres["objective"] = objectif
    parametres.update(params_supplementaires)
    _afficher_ram("avant fit lightgbm")
    modele = lgb.LGBMRegressor(**parametres)
    if len(x_valid) >= 5:
        modele.fit(
            x_train, y_train, eval_set=[(x_valid, y_valid)], eval_metric="rmse",
            callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)],
        )
    else:
        modele.fit(x_train, y_train)
    _afficher_ram("apres fit lightgbm")
    return modele


def _entrainer_simple(cle_modele, table, colonnes_features, date_coupure):
    info = MODELES[cle_modele]
    specification = SPECIFICATIONS[cle_modele]
    train, valid = _separer_train_validation(table, date_coupure)
    train = _sous_echantillonner(train, specification["taille_max"])

    x_train, y_train = train[colonnes_features], train[info["cible"]]
    x_valid, y_valid = valid[colonnes_features], valid[info["cible"]]

    if specification["format"] == "catboost":
        modele = _entrainer_catboost(x_train, y_train, x_valid, y_valid, specification["loss_function"])
    else:
        modele = _entrainer_lightgbm(x_train, y_train, x_valid, y_valid, specification["objectif_lgbm"], specification["params_supplementaires"])

    predictions = np.clip(modele.predict(x_valid), 0, None)
    metriques = _calculer_metriques(y_valid, predictions)
    return {"unique": modele}, metriques, len(train)


def _entrainer_multi_categorie(cle_modele, table, colonnes_features, date_coupure):
    info = MODELES[cle_modele]
    specification = SPECIFICATIONS[cle_modele]
    categories = sorted(table[info["colonne_categorie"]].dropna().unique())

    modeles = {}
    parties_validation = []
    nb_lignes_train = 0

    for categorie in categories:
        sous_table = table[table[info["colonne_categorie"]] == categorie]
        train, valid = _separer_train_validation(sous_table, date_coupure)
        train = _sous_echantillonner(train, specification["taille_max"])
        if len(train) < 50:
            continue

        x_train, y_train = train[colonnes_features], train[info["cible"]]
        x_valid = valid[colonnes_features] if len(valid) else train[colonnes_features].iloc[:0]
        y_valid = valid[info["cible"]] if len(valid) else train[info["cible"]].iloc[:0]

        modele = _entrainer_lightgbm(x_train, y_train, x_valid, y_valid, specification["objectif_lgbm"], specification["params_supplementaires"])
        modeles[str(categorie)] = modele
        nb_lignes_train += len(train)

        if len(valid):
            predictions_brutes = np.clip(modele.predict(x_valid), 0, None)
            parties_validation.append(valid.assign(prediction_brute=predictions_brutes))

    if not parties_validation:
        return modeles, {"RMSE": None, "MAE": None}, nb_lignes_train

    validation_complete = pd.concat(parties_validation)
    predictions_normalisees = _normaliser_par_groupe(validation_complete, validation_complete["prediction_brute"].values)
    metriques = _calculer_metriques(validation_complete[info["cible"]], predictions_normalisees)
    return modeles, metriques, nb_lignes_train


def _evaluer_ancien_modele_meme_periode(cle_modele, table, colonnes_features, date_coupure):
    info = MODELES[cle_modele]
    specification = SPECIFICATIONS[cle_modele]
    _, valid = _separer_train_validation(table, date_coupure)

    if specification["composition"]:
        mapping_chemin = os.path.join(info["dossier"], info["mapping_modeles"])
        if not os.path.isfile(mapping_chemin):
            return None
        modeles = charger_modeles_categorie(cle_modele)
        parties = []
        for categorie, modele in modeles.items():
            sous_valid = valid[valid[info["colonne_categorie"]].astype(str) == str(categorie)]
            if sous_valid.empty:
                continue
            predictions_brutes = np.clip(modele.predict(sous_valid[colonnes_features]), 0, None)
            parties.append(sous_valid.assign(prediction_brute=predictions_brutes))
        if not parties:
            return None
        validation_complete = pd.concat(parties)
        predictions_normalisees = _normaliser_par_groupe(validation_complete, validation_complete["prediction_brute"].values)
        metriques = _calculer_metriques(validation_complete[info["cible"]], predictions_normalisees)
        return metriques["RMSE"]

    if not os.path.isfile(chemin_modele(cle_modele)):
        return None
    if len(valid) == 0:
        return None

    modele = charger_modele_simple(cle_modele)
    predictions = np.clip(modele.predict(valid[colonnes_features]), 0, None)
    metriques = _calculer_metriques(valid[info["cible"]], predictions)
    return metriques["RMSE"]


def _sauvegarder_modele(chemin, modele, format_modele):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    if format_modele == "catboost":
        modele.save_model(chemin)
    else:
        modele.booster_.save_model(chemin)


def _metriques_actuelles(cle_modele):
    chemin = chemin_fichier(cle_modele, "metriques")
    if not os.path.isfile(chemin):
        return None
    with open(chemin, "r") as fichier:
        return json.load(fichier)


def _ecrire_metriques(cle_modele, metriques):
    with open(chemin_fichier(cle_modele, "metriques"), "w") as fichier:
        json.dump(metriques, fichier, indent=2)


def _ecrire_log(entree):
    os.makedirs(os.path.dirname(LOG_EXECUTION), exist_ok=True)
    journal = []
    if os.path.isfile(LOG_EXECUTION):
        with open(LOG_EXECUTION, "r") as fichier:
            journal = json.load(fichier)
    journal.append(entree)
    with open(LOG_EXECUTION, "w") as fichier:
        json.dump(journal, fichier, indent=2, default=str)


def reentrainer(cle_modele):
    info = MODELES[cle_modele]
    specification = SPECIFICATIONS[cle_modele]
    horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chemin_historique = _chemin_historique(cle_modele)

    if not os.path.isfile(chemin_historique):
        resultat = {"horodatage": horodatage, "type": "reentrainement", "cle_modele": cle_modele, "statut": "echec", "erreur": "historique_absent"}
        _ecrire_log(resultat)
        return resultat

    historique = pd.read_parquet(chemin_historique)
    _afficher_ram("apres lecture historique")

    table = construire_table_entrainement(cle_modele, historique)
    del historique
    table = table.dropna(subset=[info["cible"]])
    _afficher_ram("apres dropna cible")

    table, encodage = _encoder_liaison(cle_modele, table)
    _afficher_ram("apres encoder_liaison")

    colonnes_attendues = json.load(open(chemin_fichier(cle_modele, "colonnes_features")))
    for colonne in colonnes_attendues:
        if colonne not in table.columns:
            table[colonne] = np.nan
    table = table.dropna(subset=colonnes_attendues)
    _afficher_ram("apres dropna colonnes_attendues")

    if len(table) < 200:
        resultat = {"horodatage": horodatage, "type": "reentrainement", "cle_modele": cle_modele, "statut": "echec", "erreur": "historique_insuffisant"}
        _ecrire_log(resultat)
        return resultat

    colonnes_modele = colonnes_attendues
    date_coupure = _dates_coupure(table)

    anciennes_metriques = _metriques_actuelles(cle_modele)

    if specification["composition"]:
        modeles, metriques_globales, nb_lignes = _entrainer_multi_categorie(cle_modele, table, colonnes_modele, date_coupure)
    else:
        modeles, metriques_globales, nb_lignes = _entrainer_simple(cle_modele, table, colonnes_modele, date_coupure)

    if metriques_globales.get("RMSE") is not None:
        metriques_globales["Cible"] = info["cible"]
        metriques_globales["Modele"] = f"{info['libelle_court'].upper()} - REENTRAINEMENT AUTOMATIQUE"

    rmse_ancien_meme_periode = _evaluer_ancien_modele_meme_periode(cle_modele, table, colonnes_modele, date_coupure)
    seuil_ancien = rmse_ancien_meme_periode
    if seuil_ancien is None:
        seuil_ancien = anciennes_metriques.get("RMSE") if anciennes_metriques else None

    accepte = seuil_ancien is None or metriques_globales.get("RMSE") is None or metriques_globales["RMSE"] <= seuil_ancien * TOLERANCE_REGRESSION

    if not accepte:
        resultat = {
            "horodatage": horodatage, "type": "reentrainement", "cle_modele": cle_modele, "statut": "rejete",
            "metriques_avant": anciennes_metriques, "metriques_apres": metriques_globales,
            "rmse_ancien_meme_periode": rmse_ancien_meme_periode,
        }
        _ecrire_log(resultat)
        return resultat

    if specification["composition"]:
        mapping_modeles = {}
        for categorie, modele in modeles.items():
            nom_fichier = f"{categorie}.txt"
            mapping_modeles[categorie] = nom_fichier
            _sauvegarder_modele(chemin_modele(cle_modele, nom_fichier), modele, "lightgbm")
        with open(os.path.join(info["dossier"], info["mapping_modeles"]), "w") as fichier:
            json.dump(mapping_modeles, fichier, indent=2)
    else:
        _sauvegarder_modele(chemin_modele(cle_modele), modeles["unique"], specification["format"])

    if encodage is not None:
        encodage.to_csv(chemin_fichier(cle_modele, "encodage_liaison"), index=False)

    metriques_globales["DateReentrainement"] = horodatage
    metriques_globales["NbLignesEntrainement"] = int(nb_lignes)
    _ecrire_metriques(cle_modele, metriques_globales)

    resultat = {
        "horodatage": horodatage, "type": "reentrainement", "cle_modele": cle_modele, "statut": "deploye",
        "metriques_avant": anciennes_metriques, "metriques_apres": metriques_globales,
        "rmse_ancien_meme_periode": rmse_ancien_meme_periode,
    }
    _ecrire_log(resultat)
    return resultat


def reentrainer_tous():
    resultats = {}
    for cle_modele in MODELES:
        try:
            resultats[cle_modele] = reentrainer(cle_modele)
        except Exception as exception:
            resultats[cle_modele] = {"statut": "erreur", "erreur": str(exception)}
    return resultats


if __name__ == "__main__":
    import argparse

    analyseur = argparse.ArgumentParser()
    analyseur.add_argument("--modele", default=None)
    arguments = analyseur.parse_args()

    if arguments.modele:
        print(json.dumps(reentrainer(arguments.modele), indent=2, default=str))
    else:
        print(json.dumps(reentrainer_tous(), indent=2, default=str))
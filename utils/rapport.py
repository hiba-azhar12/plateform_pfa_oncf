import os
from datetime import datetime, timedelta

import pandas as pd
from fpdf import FPDF

from config.chemins import RAPPORTS
from config.modeles import MODELES, MODELES_PAR_DOMAINE
from utils.chargement import (
    charger_anomalies,
    charger_comparaison_inter_annees,
    charger_metriques,
    charger_predictions,
    charger_predictions_nouvelles,
    charger_seuil_anomalie,
)
from utils.graphiques_rapport import (
    graphique_barres_wmape,
    graphique_comparaison_annuelle,
    graphique_histogramme,
    graphique_repartition_categorie,
    graphique_serie_temporelle,
)
from utils.style import CHEMIN_LOGO_ONCF, CHEMIN_LOGO_TRAIN, PALETTE
from utils.texte import severite_anomalie

LARGEUR_PAGE = 210
MARGE = 15
LARGEUR_UTILE = LARGEUR_PAGE - 2 * MARGE
COULEUR_ENTETE_TABLEAU = "#FBE0C2"
LIBELLES_SEVERITE = {"critique": "Critique", "moderee": "Modérée", "faible": "Faible"}


def _rgb(couleur_hex):
    couleur_hex = couleur_hex.lstrip("#")
    return tuple(int(couleur_hex[indice:indice + 2], 16) for indice in (0, 2, 4))


def _texte_court(valeur, longueur=28):
    valeur = str(valeur)
    return valeur if len(valeur) <= longueur else valeur[:longueur - 3] + "..."


class RapportONCF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(MARGE, MARGE, MARGE)
        self.logo_disponible = os.path.isfile(CHEMIN_LOGO_ONCF)
        self.train_disponible = os.path.isfile(CHEMIN_LOGO_TRAIN)
        self.fichiers_temporaires = []

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*_rgb(PALETTE["navy"]))
        self.rect(0, 0, LARGEUR_PAGE, 16, "F")
        if self.logo_disponible:
            self.image(CHEMIN_LOGO_ONCF, x=MARGE, y=3, h=10)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(255, 255, 255)
        self.set_xy(0, 6)
        self.cell(LARGEUR_PAGE - MARGE, 6, "Rapport hebdomadaire de performance commerciale", align="R")
        self.set_fill_color(*_rgb(PALETTE["orange"]))
        self.rect(0, 16, LARGEUR_PAGE, 1.4, "F")
        self.set_y(23)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_rgb(PALETTE["muted"]))
        self.cell(0, 8, f"ONCF - Document interne - Page {self.page_no()}", align="C")

    def page_de_couverture(self, periode_texte):
        self.add_page()
        self.set_fill_color(*_rgb(PALETTE["navy"]))
        self.rect(0, 0, LARGEUR_PAGE, 95, "F")
        self.set_fill_color(*_rgb(PALETTE["orange"]))
        self.rect(0, 95, LARGEUR_PAGE, 3, "F")
        if self.logo_disponible:
            self.image(CHEMIN_LOGO_ONCF, x=MARGE, y=14, h=24)
        if self.train_disponible:
            self.image(CHEMIN_LOGO_TRAIN, x=MARGE, y=68, w=LARGEUR_UTILE)
        self.set_xy(MARGE, 112)
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(*_rgb(PALETTE["navy"]))
        self.multi_cell(LARGEUR_UTILE, 11, "Rapport hebdomadaire de\nperformance commerciale", align="L")
        self.ln(4)
        self.set_font("Helvetica", "", 12)
        self.set_text_color(*_rgb(PALETTE["muted"]))
        self.cell(0, 8, f"Période couverte : {periode_texte}", ln=True)
        self.cell(0, 8, f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", ln=True)
        self.ln(12)
        self.set_draw_color(*_rgb(PALETTE["orange"]))
        self.set_line_width(0.7)
        self.line(MARGE, self.get_y(), LARGEUR_PAGE - MARGE, self.get_y())
        self.set_y(-30)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_rgb(PALETTE["muted"]))
        self.cell(0, 6, "DSID - Rapport généré par la Plateforme Performance Commerciale pour PDA", align="C")

    def titre_section(self, texte, sous_texte=None):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(*_rgb(PALETTE["navy"]))
        self.cell(0, 9, texte, ln=True)
        if sous_texte:
            self.set_font("Helvetica", "", 9.5)
            self.set_text_color(*_rgb(PALETTE["muted"]))
            self.cell(0, 6, sous_texte, ln=True)
        self.set_draw_color(*_rgb(PALETTE["orange"]))
        self.set_line_width(0.8)
        self.line(MARGE, self.get_y() + 1, LARGEUR_PAGE - MARGE, self.get_y() + 1)
        self.ln(6)

    def sous_titre_modele(self, texte, accent="navy"):
        if self.get_y() + 34 > self.h - self.b_margin:
            self.add_page()
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*_rgb(PALETTE[accent]))
        self.cell(0, 8, texte, ln=True)
        self.ln(1)

    def cartes_kpi(self, valeurs, accent="navy"):
        nombre = len(valeurs)
        marge_carte = 4
        largeur_carte = (LARGEUR_UTILE - marge_carte * (nombre - 1)) / nombre
        hauteur = 19
        if self.get_y() + hauteur > self.h - self.b_margin:
            self.add_page()
        x = MARGE
        y = self.get_y()
        for label, valeur in valeurs:
            self.set_draw_color(*_rgb(PALETTE["border_carte"]))
            self.set_fill_color(255, 255, 255)
            self.rect(x, y, largeur_carte, hauteur, "DF")
            self.set_xy(x + 3, y + 2.5)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*_rgb(PALETTE["muted"]))
            self.multi_cell(largeur_carte - 6, 3.6, label, align="L")
            self.set_xy(x + 3, y + 10.5)
            self.set_font("Helvetica", "B", 13.5)
            self.set_text_color(*_rgb(PALETTE[accent]))
            self.cell(largeur_carte - 6, 7, str(valeur))
            x += largeur_carte + marge_carte
        self.set_xy(MARGE, y + hauteur + 6)

    def tableau(self, colonnes, lignes, largeurs=None):
        nombre = len(colonnes)
        if largeurs is None:
            largeurs = [LARGEUR_UTILE / nombre] * nombre
        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(*_rgb(COULEUR_ENTETE_TABLEAU))
        self.set_text_color(*_rgb(PALETTE["text"]))
        self.set_draw_color(*_rgb(PALETTE["border"]))
        for entete, largeur in zip(colonnes, largeurs):
            self.cell(largeur, 7, entete, border=1, fill=True, align="L")
        self.ln()
        self.set_font("Helvetica", "", 8.5)
        for ligne in lignes:
            for valeur, largeur in zip(ligne, largeurs):
                self.cell(largeur, 6.5, _texte_court(valeur, 32), border=1)
            self.ln()
        self.ln(4)

    def inserer_image(self, chemin, largeur=LARGEUR_UTILE):
        x = (LARGEUR_PAGE - largeur) / 2
        self.image(chemin, x=x, w=largeur)
        self.fichiers_temporaires.append(chemin)
        self.ln(3)

    def inserer_deux_images(self, chemin_gauche, chemin_droite, largeur_gauche=105, largeur_droite=65):
        y = self.get_y()
        self.image(chemin_gauche, x=MARGE, y=y, w=largeur_gauche)
        self.image(chemin_droite, x=MARGE + largeur_gauche + 6, y=y, w=largeur_droite)
        self.fichiers_temporaires.extend([chemin_gauche, chemin_droite])
        self.ln(4)

    def nettoyer_fichiers_temporaires(self):
        for chemin in self.fichiers_temporaires:
            if os.path.isfile(chemin):
                os.remove(chemin)


def _wmapes_disponibles():
    resultat = {}
    for cle_modele, info in MODELES.items():
        metriques = charger_metriques(cle_modele)
        if metriques.get("WMAPE") is not None:
            resultat[cle_modele] = metriques["WMAPE"]
    return resultat


def _nb_anomalies_totales():
    total = 0
    for cle_modele in MODELES:
        anomalies = charger_anomalies(cle_modele)
        if not anomalies.empty and "EstAnomalie" in anomalies.columns:
            total += int(anomalies["EstAnomalie"].sum())
    return total


def _volume_periode(cle_modele, jours=7):
    donnees = charger_predictions_nouvelles(cle_modele)
    if donnees.empty or "Reel" not in donnees.columns:
        return None
    donnees = donnees.copy()
    donnees["Date"] = pd.to_datetime(donnees["Date"])
    limite = donnees["Date"].max() - timedelta(days=jours)
    recent = donnees[(donnees["Date"] >= limite) & donnees["Reel"].notna()]
    if recent.empty:
        return None
    return recent["Reel"].sum()


def _serie_agregee(cle_modele, jours=30):
    info = MODELES[cle_modele]
    donnees = charger_predictions_nouvelles(cle_modele)
    colonne_cible = "Reel"
    if donnees.empty or donnees["Reel"].isna().all():
        donnees = charger_predictions(cle_modele)
        colonne_cible = info["cible"]
    if donnees.empty:
        return None
    donnees = donnees.copy()
    donnees["Date"] = pd.to_datetime(donnees["Date"])
    limite = donnees["Date"].max() - timedelta(days=jours)
    recent = donnees[donnees["Date"] >= limite]
    fonction = "sum" if info["famille"] == "comptages" else "mean"
    agrege = recent.groupby("Date", as_index=False).agg({colonne_cible: fonction, "Prediction": fonction}).sort_values("Date")
    agrege = agrege.dropna(subset=[colonne_cible])
    if agrege.empty:
        return None
    return agrege, colonne_cible


def _top_liaisons_ecart(cle_modele, n=5):
    anomalies = charger_anomalies(cle_modele)
    if anomalies.empty or "LiaisonId" not in anomalies.columns:
        return pd.DataFrame()
    return anomalies.sort_values("ErreurAbsolue", ascending=False).head(n)


def _repartition_categorie(cle_modele):
    info = MODELES[cle_modele]
    donnees = charger_predictions(cle_modele)
    if donnees.empty or info["colonne_categorie"] not in donnees.columns:
        return None
    moyennes = donnees.groupby(info["colonne_categorie"]).agg({info["cible"]: "mean", "Prediction": "mean"})
    moyennes = moyennes.sort_values(info["cible"], ascending=False)
    if moyennes.empty:
        return None
    return moyennes


def _comparaison_annuelle(cle_modele):
    info = MODELES[cle_modele]
    donnees = charger_comparaison_inter_annees(cle_modele)
    colonnes_requises = {"Annee", "Mois", info["cible"]}
    if donnees.empty or not colonnes_requises.issubset(donnees.columns):
        return None
    resultat = {}
    for annee, groupe in donnees.groupby("Annee"):
        groupe = groupe.sort_values("Mois")
        resultat[int(annee)] = (groupe["Mois"].tolist(), groupe[info["cible"]].tolist())
    if len(resultat) < 2:
        return None
    return resultat


def _anomalies_consolidees(n=25):
    lignes = []
    for cle_modele in MODELES:
        info = MODELES[cle_modele]
        anomalies = charger_anomalies(cle_modele)
        if anomalies.empty or "EstAnomalie" not in anomalies.columns:
            continue
        seuil_info = charger_seuil_anomalie(cle_modele)
        seuil = seuil_info.get("SeuilAnomalie", 0)
        detectees = anomalies[anomalies["EstAnomalie"]].copy()
        if detectees.empty:
            continue
        detectees["Severite"] = detectees["ErreurAbsolue"].apply(lambda erreur: severite_anomalie(erreur, seuil))
        detectees["Modele"] = info["libelle_court"]
        detectees["Ecart"] = detectees["Prediction"] - detectees[info["cible"]]
        lignes.append(detectees[["Modele", "Date", "LiaisonId", "ErreurAbsolue", "Ecart", "Severite"]])
    if not lignes:
        return pd.DataFrame()
    consolide = pd.concat(lignes, ignore_index=True).sort_values("ErreurAbsolue", ascending=False)
    return consolide.head(n)


def _section_modele(document, cle_modele, accent="navy"):
    info = MODELES[cle_modele]
    metriques = charger_metriques(cle_modele)

    document.sous_titre_modele(info["libelle"], accent=accent)

    valeurs_kpi = []
    for cle, libelle in (("RMSE", "RMSE"), ("MAE", "MAE"), ("WMAPE", "WMAPE"), ("LogLossComposition", "LogLoss")):
        if metriques.get(cle) is not None:
            valeurs_kpi.append((libelle, f"{round(metriques[cle], 3)}"))
    if valeurs_kpi:
        document.cartes_kpi(valeurs_kpi[:4], accent=accent)

    if info["multi_categorie"]:
        repartition = _repartition_categorie(cle_modele)
        if repartition is not None:
            chemin_graphe = graphique_repartition_categorie(
                repartition.index.tolist(),
                repartition[info["cible"]].tolist(),
                repartition["Prediction"].tolist(),
                f"{info['libelle_court']} - Réel vs Prédiction moyens par {info['colonne_categorie']}",
            )
            document.inserer_image(chemin_graphe)
        else:
            document.set_font("Helvetica", "", 9)
            document.set_text_color(*_rgb(PALETTE["muted"]))
            document.cell(0, 6, "Aucune donnée de répartition disponible pour ce modèle.", ln=True)
    else:
        resultat_serie = _serie_agregee(cle_modele)
        if resultat_serie is not None:
            agrege, colonne_cible = resultat_serie
            chemin_graphe = graphique_serie_temporelle(
                agrege["Date"], agrege[colonne_cible], agrege["Prediction"],
                f"{info['libelle_court']} - Réel vs Prédiction (agrégé, toutes liaisons)",
            )
            document.inserer_image(chemin_graphe)
        else:
            document.set_font("Helvetica", "", 9)
            document.set_text_color(*_rgb(PALETTE["muted"]))
            document.cell(0, 6, "Aucune série récente disponible pour ce modèle.", ln=True)

    top_liaisons = _top_liaisons_ecart(cle_modele)
    if not top_liaisons.empty:
        document.set_font("Helvetica", "B", 9.5)
        document.set_text_color(*_rgb(PALETTE["navy"]))
        document.cell(0, 6, "Top 5 des liaisons avec l'écart le plus important", ln=True)
        document.ln(1)
        colonne_cible_libelle = info["cible"]
        lignes = [
            [ligne["Date"], ligne["LiaisonId"], round(ligne[colonne_cible_libelle], 2), round(ligne["Prediction"], 2), round(ligne["ErreurAbsolue"], 2)]
            for _, ligne in top_liaisons.iterrows()
        ]
        document.tableau(
            ["Date", "Liaison", "Réel", "Prédiction", "Écart absolu"],
            lignes,
            largeurs=[32, 30, 34, 40, 44],
        )
    else:
        document.ln(2)


def generer_rapport_hebdomadaire():
    os.makedirs(RAPPORTS, exist_ok=True)

    date_limite = datetime.now() - timedelta(days=7)
    periode_texte = f"{date_limite.strftime('%d/%m/%Y')} - {datetime.now().strftime('%d/%m/%Y')}"

    document = RapportONCF()
    document.page_de_couverture(periode_texte)

    document.add_page()
    document.titre_section("Synthèse exécutive", "Vue d'ensemble des 7 modèles de prédiction")

    wmapes = _wmapes_disponibles()
    nb_anomalies = _nb_anomalies_totales()
    volume_ventes = _volume_periode("modele1_ventes")
    volume_controles = _volume_periode("modele3_controles")

    meilleur_modele = min(wmapes, key=wmapes.get) if wmapes else None
    pire_modele = max(wmapes, key=wmapes.get) if wmapes else None

    valeurs_kpi = [
        ("Anomalies détectées (test)", str(nb_anomalies)),
        ("WMAPE moyen", f"{round(sum(wmapes.values()) / len(wmapes), 1)}%" if wmapes else "-"),
        ("Volume vendu (7 j)", f"{volume_ventes:,.0f}".replace(",", " ") if volume_ventes is not None else "n/d"),
        ("Volume contrôlé (7 j)", f"{volume_controles:,.0f}".replace(",", " ") if volume_controles is not None else "n/d"),
    ]
    document.cartes_kpi(valeurs_kpi)

    if wmapes:
        libelles = [MODELES[cle]["libelle_court"] for cle in wmapes]
        valeurs = list(wmapes.values())
        chemin_graphe = graphique_barres_wmape(libelles, valeurs)
        document.inserer_image(chemin_graphe)

    document.set_font("Helvetica", "", 9.5)
    document.set_text_color(*_rgb(PALETTE["text"]))
    if meilleur_modele and pire_modele:
        phrase = (
            f"Cette semaine, {MODELES[meilleur_modele]['libelle_court']} est le modèle le plus fiable "
            f"(WMAPE {round(wmapes[meilleur_modele], 1)}%), tandis que {MODELES[pire_modele]['libelle_court']} "
            f"présente l'écart le plus important (WMAPE {round(wmapes[pire_modele], 1)}%). "
            f"{nb_anomalies} anomalie(s) ont été détectées au total sur le jeu de test des 7 modèles."
        )
    else:
        phrase = f"{nb_anomalies} anomalie(s) ont été détectées au total sur le jeu de test des 7 modèles."
    document.multi_cell(LARGEUR_UTILE, 6, phrase)

    document.add_page()
    document.titre_section("Ventes", "Billets vendus, taux de vente guichet, répartition par confort")
    for cle_modele in MODELES_PAR_DOMAINE["ventes"]:
        _section_modele(document, cle_modele)
        document.ln(4)

    document.add_page()
    document.titre_section("Contrôles", "Billets contrôlés, taux de contrôle, taux de fraude, répartition par titre")
    for cle_modele in MODELES_PAR_DOMAINE["controles"]:
        accent = "red" if cle_modele == "modele6_taux_fraude" else "navy"
        _section_modele(document, cle_modele, accent=accent)
        document.ln(4)

    document.add_page()
    document.titre_section("Anomalies critiques", "Vue consolidée toutes familles de modèles")
    consolide = _anomalies_consolidees()
    if not consolide.empty:
        lignes = [
            [ligne["Modele"], ligne["Date"], ligne["LiaisonId"], round(ligne["Ecart"], 2), LIBELLES_SEVERITE.get(ligne["Severite"], ligne["Severite"])]
            for _, ligne in consolide.iterrows()
        ]
        document.tableau(
            ["Modèle", "Date", "Liaison", "Écart (préd. - réel)", "Sévérité"],
            lignes,
            largeurs=[46, 30, 26, 46, 32],
        )
        chemin_histogramme = graphique_histogramme(consolide["Ecart"].tolist(), "Distribution des écarts (anomalies consolidées)")
        document.inserer_image(chemin_histogramme)
    else:
        document.set_font("Helvetica", "", 9.5)
        document.set_text_color(*_rgb(PALETTE["muted"]))
        document.cell(0, 6, "Aucune anomalie détectée sur le jeu de test des 7 modèles.", ln=True)

    comparaisons = {cle: _comparaison_annuelle(cle) for cle in MODELES}
    comparaisons = {cle: valeur for cle, valeur in comparaisons.items() if valeur is not None}
    if comparaisons:
        document.add_page()
        document.titre_section("Comparaison inter-annuelle", "Évolution mensuelle par rapport à l'année précédente")
        for cle_modele, donnees_annees in comparaisons.items():
            info = MODELES[cle_modele]
            chemin_graphe = graphique_comparaison_annuelle(donnees_annees, info["libelle"])
            document.inserer_image(chemin_graphe)
            document.ln(2)

    document.add_page()
    document.titre_section("Annexe", "Légende, méthodologie et périmètre des modèles")

    document.set_font("Helvetica", "B", 10)
    document.set_text_color(*_rgb(PALETTE["navy"]))
    document.cell(0, 7, "Légende des seuils de sévérité", ln=True)
    document.set_font("Helvetica", "", 9)
    document.set_text_color(*_rgb(PALETTE["text"]))
    document.multi_cell(
        LARGEUR_UTILE, 6,
        "Faible : écart inférieur au seuil statistique du modèle.\n"
        "Modérée : écart supérieur au seuil, inférieur à deux fois le seuil.\n"
        "Critique : écart supérieur à deux fois le seuil (moyenne + 2 écarts-types des erreurs du jeu de test).",
    )
    document.ln(4)

    document.set_font("Helvetica", "B", 10)
    document.set_text_color(*_rgb(PALETTE["navy"]))
    document.cell(0, 7, "Périmètre des modèles", ln=True)
    document.ln(1)
    lignes_modeles = [
        [info["libelle_court"], info["domaine"].capitalize(), info["format_modele"].capitalize(), info["granularite"].capitalize()]
        for info in MODELES.values()
    ]
    document.tableau(["Modèle", "Domaine", "Algorithme", "Granularité"], lignes_modeles, largeurs=[64, 34, 40, 42])

    nom_fichier = f"rapport_hebdomadaire_{datetime.now().strftime('%Y%m%d')}.pdf"
    chemin = os.path.join(RAPPORTS, nom_fichier)
    document.output(chemin)
    document.nettoyer_fichiers_temporaires()
    return chemin
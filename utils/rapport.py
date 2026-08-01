import os
from datetime import datetime, timedelta

import pandas as pd
from fpdf import FPDF

from config.chemins import RAPPORTS
from config.modeles import MODELES
from utils.chargement import charger_anomalies, charger_metriques


class RapportONCF(FPDF):
    def entete_page(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(11, 37, 69)
        self.cell(0, 12, "ONCF - Rapport hebdomadaire de performance commerciale", ln=True)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(90, 96, 104)
        self.cell(0, 8, f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", ln=True)
        self.ln(4)
        self.set_draw_color(11, 37, 69)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def section_modele(self, titre, metriques, anomalies_recentes):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(11, 37, 69)
        self.cell(0, 9, titre, ln=True)

        self.set_font("Helvetica", "", 10)
        self.set_text_color(28, 31, 38)

        for cle in ("RMSE", "MAE", "WMAPE", "LogLossComposition"):
            if cle in metriques:
                valeur = metriques[cle]
                if isinstance(valeur, float):
                    valeur = round(valeur, 3)
                self.cell(0, 6, f"{cle} : {valeur}", ln=True)

        self.cell(0, 6, f"Anomalies détectées cette semaine : {len(anomalies_recentes)}", ln=True)

        if not anomalies_recentes.empty:
            for _, ligne in anomalies_recentes.head(5).iterrows():
                texte = f"  {ligne['Date']} - liaison {ligne['LiaisonId']} - écart {ligne['ErreurAbsolue']:.0f}"
                self.multi_cell(0, 5, texte)

        self.ln(4)


def generer_rapport_hebdomadaire():
    os.makedirs(RAPPORTS, exist_ok=True)
    date_limite = datetime.now() - timedelta(days=7)

    document = RapportONCF()
    document.add_page()
    document.entete_page()

    for cle_modele, info in MODELES.items():
        metriques = charger_metriques(cle_modele)
        anomalies = charger_anomalies(cle_modele)

        if not anomalies.empty and "Date" in anomalies.columns:
            anomalies = anomalies.copy()
            anomalies["Date"] = pd.to_datetime(anomalies["Date"])
            anomalies_recentes = anomalies[
                (anomalies["Date"] >= date_limite) & (anomalies["EstAnomalie"])
            ].sort_values("ErreurAbsolue", ascending=False)
        else:
            anomalies_recentes = pd.DataFrame()

        document.section_modele(info["libelle"], metriques, anomalies_recentes)

    nom_fichier = f"rapport_hebdomadaire_{datetime.now().strftime('%Y%m%d')}.pdf"
    chemin = os.path.join(RAPPORTS, nom_fichier)
    document.output(chemin)
    return chemin

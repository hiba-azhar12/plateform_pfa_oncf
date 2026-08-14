import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utils.style import PALETTE

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["text.color"] = PALETTE["text"]
plt.rcParams["axes.edgecolor"] = PALETTE["border"]
plt.rcParams["axes.labelcolor"] = PALETTE["text"]
plt.rcParams["xtick.color"] = PALETTE["muted"]
plt.rcParams["ytick.color"] = PALETTE["muted"]


def _nouveau_fichier_temp():
    fichier = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fichier.close()
    return fichier.name


def _finaliser(figure):
    figure.tight_layout()
    chemin = _nouveau_fichier_temp()
    figure.savefig(chemin, dpi=200, transparent=True)
    plt.close(figure)
    return chemin


def graphique_barres_wmape(libelles, valeurs):
    figure, axe = plt.subplots(figsize=(7.4, 0.5 + 0.42 * len(libelles)))
    couleurs = [PALETTE["red"] if v > 20 else PALETTE["orange"] if v > 5 else PALETTE["steel"] for v in valeurs]
    positions = range(len(libelles))
    axe.barh(list(positions), valeurs, color=couleurs, height=0.55)
    axe.set_yticks(list(positions))
    axe.set_yticklabels(libelles, fontsize=9)
    axe.invert_yaxis()
    axe.set_xlabel("WMAPE (%)", fontsize=9)
    axe.spines["top"].set_visible(False)
    axe.spines["right"].set_visible(False)
    for position, valeur in zip(positions, valeurs):
        axe.text(valeur, position, f"  {valeur:.1f}%", va="center", fontsize=8.5, color=PALETTE["text"])
    return _finaliser(figure)


def graphique_serie_temporelle(dates, reel, prediction, titre):
    figure, axe = plt.subplots(figsize=(7.4, 2.5))
    axe.plot(dates, prediction, color=PALETTE["orange"], linewidth=2, label="Prédiction")
    axe.plot(dates, reel, color=PALETTE["navy"], linewidth=2, label="Réel")
    axe.legend(frameon=False, fontsize=8.5, loc="upper left")
    axe.spines["top"].set_visible(False)
    axe.spines["right"].set_visible(False)
    axe.set_title(titre, fontsize=9.5, loc="left", color=PALETTE["text"], fontweight="bold")
    axe.tick_params(labelsize=8)
    figure.autofmt_xdate(rotation=25)
    return _finaliser(figure)


def graphique_repartition_categorie(categories, valeurs_reelles, valeurs_predites, titre):
    figure, axe = plt.subplots(figsize=(7.4, 2.6))
    positions = range(len(categories))
    largeur = 0.35
    axe.bar([p - largeur / 2 for p in positions], valeurs_reelles, width=largeur, color=PALETTE["navy"], label="Réel")
    axe.bar([p + largeur / 2 for p in positions], valeurs_predites, width=largeur, color=PALETTE["orange"], label="Prédiction")
    axe.set_xticks(list(positions))
    axe.set_xticklabels(categories, fontsize=8.5)
    axe.legend(frameon=False, fontsize=8.5, loc="upper right")
    axe.spines["top"].set_visible(False)
    axe.spines["right"].set_visible(False)
    axe.set_title(titre, fontsize=9.5, loc="left", color=PALETTE["text"], fontweight="bold")
    axe.tick_params(labelsize=8)
    return _finaliser(figure)


def graphique_histogramme(valeurs, titre):
    figure, axe = plt.subplots(figsize=(7.4, 2.2))
    axe.hist(valeurs, bins=25, color=PALETTE["amber"], edgecolor="none")
    axe.spines["top"].set_visible(False)
    axe.spines["right"].set_visible(False)
    axe.set_title(titre, fontsize=9.5, loc="left", color=PALETTE["text"], fontweight="bold")
    axe.set_xlabel("Écart (prédiction − réel)", fontsize=8.5)
    axe.set_ylabel("Fréquence", fontsize=8.5)
    axe.tick_params(labelsize=8)
    return _finaliser(figure)


def graphique_comparaison_annuelle(donnees_par_annee, titre):
    figure, axe = plt.subplots(figsize=(7.4, 2.4))
    couleurs = [PALETTE["muted"], PALETTE["orange"], PALETTE["navy"]]
    for indice, (annee, (mois, valeurs)) in enumerate(donnees_par_annee.items()):
        axe.plot(mois, valeurs, marker="o", markersize=3, linewidth=2, color=couleurs[indice % len(couleurs)], label=str(annee))
    axe.legend(frameon=False, fontsize=8.5, loc="upper left")
    axe.spines["top"].set_visible(False)
    axe.spines["right"].set_visible(False)
    axe.set_title(titre, fontsize=9.5, loc="left", color=PALETTE["text"], fontweight="bold")
    axe.set_xticks(range(1, 13))
    axe.tick_params(labelsize=8)
    return _finaliser(figure)
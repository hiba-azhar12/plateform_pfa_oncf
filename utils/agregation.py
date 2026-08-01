from utils.feature_engineering import (
    construire_modele1,
    construire_modele2,
    construire_modele3,
    construire_modele4,
    construire_modele5,
    construire_modele6,
    construire_modele7,
    pivot_circulation,
    pivot_controles,
    pivot_ventes,
)


def agreger_lot_quotidien(ventepda, controlepda, circulation):
    pivot_vente = pivot_ventes(ventepda)
    pivot_controle = pivot_controles(controlepda)
    pivot_circ = pivot_circulation(circulation)

    return {
        "modele1_ventes": construire_modele1(pivot_vente),
        "modele2_taux_vente_guichet": construire_modele2(pivot_vente, pivot_circ),
        "modele4_part_confort": construire_modele4(pivot_vente),
        "modele3_controles": construire_modele3(pivot_controle),
        "modele5_taux_controle": construire_modele5(pivot_controle, pivot_circ),
        "modele6_taux_fraude": construire_modele6(pivot_controle),
        "modele7_part_type": construire_modele7(pivot_controle),
    }

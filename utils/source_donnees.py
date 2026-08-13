from abc import ABC, abstractmethod


class SourceDonnees(ABC):
    @abstractmethod
    def recuperer_fichiers_du_jour(self):
        raise NotImplementedError


class SourceDonneesDrive(SourceDonnees):
    def recuperer_fichiers_du_jour(self):
        from scripts.telecharger_depot import telecharger_nouveaux_fichiers
        return telecharger_nouveaux_fichiers()


class SourceDonneesBaseONCF(SourceDonnees):
    def __init__(self, chaine_connexion):
        self.chaine_connexion = chaine_connexion

    def recuperer_fichiers_du_jour(self):
        raise NotImplementedError


def obtenir_source_active():
    return SourceDonneesDrive()
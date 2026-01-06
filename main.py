"""
main.py
Point d'entrée du bot CS2.
"""

import os
from modules import RecuperateurCS2, GestionEtat, NotifDiscord

URL_MISES_A_JOUR = "https://www.counter-strike.net/news/updates?l=french"
URL_ACTUALITES = "https://www.counter-strike.net/news"

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("Le secret DISCORD_WEBHOOK_URL est manquant.")


class BotCS2:
    """Orchestre la récupération, l'envoi et l'enregistrement des articles."""

    def __init__(self):
        self.recuperateur = RecuperateurCS2()
        self.etat = GestionEtat()
        self.notif = NotifDiscord(WEBHOOK_URL)

    def run(self):
        sources = [
            (URL_MISES_A_JOUR, "mise_a_jour"),
            (URL_ACTUALITES, "actualite")
        ]

        for url, categorie in sources:
            article = self.recuperateur.recuperer(url, categorie)
            if not article:
                continue

            article_id = article.get_id()
            print(f"ID : {article_id}")

            if self.etat.deja_envoye(article_id):
                print("⏩ Déjà envoyé.")
                continue

            self.notif.envoyer(article)
            self.etat.enregistrer(article_id)
            print("✅ Envoyé et enregistré.")


if __name__ == "__main__":
    BotCS2().run()

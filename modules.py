"""
modules.py
Contient toutes les classes utilisées par le bot CS2 :
- ArticleCS2 : modèle de données
- GestionEtat : gestion du fichier last_sent.txt
- NotifDiscord : envoi des messages Discord
- RecuperateurCS2 : récupération des mises à jour et actualités via Playwright
"""

import os
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# === Modèle de données ===
class ArticleCS2:
    """Représente un article CS2 (mise à jour ou actualité)."""

    def __init__(self, titre: str, resume: str, lien: str, categorie: str):
        self.titre = titre
        self.resume = resume
        self.lien = lien
        self.categorie = categorie

    def get_id(self) -> str:
        """Génère un identifiant unique basé sur le contenu."""
        contenu = (self.titre + self.resume + self.categorie).strip()
        return hashlib.md5(contenu.encode("utf-8")).hexdigest()


# === Gestion de l'état ===
class GestionEtat:
    """Gère le fichier contenant les IDs déjà envoyés."""

    def __init__(self, chemin="last_sent.txt"):
        self.chemin = chemin

    def deja_envoye(self, article_id: str) -> bool:
        if not os.path.exists(self.chemin):
            return False
        with open(self.chemin, "r", encoding="utf-8") as f:
            return article_id in f.read().splitlines()

    def enregistrer(self, article_id: str):
        with open(self.chemin, "a", encoding="utf-8") as f:
            f.write(article_id + "\n")


# === Notification Discord ===
class NotifDiscord:
    """Envoie un article CS2 sur Discord via un webhook."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def envoyer(self, article: ArticleCS2):
        titre, date = article.titre.rsplit("(", 1)
        titre = titre.strip()
        date = date.strip(")")

        description = f"""📅 {date}

📝 **{titre}**

{article.resume}"""

        payload = {
            "embeds": [{
                "title": "📰 Nouvelle mise à jour CS2 !",
                "url": article.lien,
                "description": description[:1024],
                "color": 0x58A6FF
            }]
        }

        print(f"📢 Envoi Discord : {article.titre}")
        resp = requests.post(self.webhook_url, json=payload, timeout=20)

        if resp.status_code >= 400:
            print("❌ Erreur Discord :", resp.text)

        resp.raise_for_status()


# === Récupération des articles ===
class RecuperateurCS2:
    """Récupère les mises à jour et actualités CS2 via Playwright."""

    def __init__(self):
        self.playwright = None
        self.browser = None

    def _demarrer(self):
        if self.playwright is None:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)

    def _arreter(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def recuperer(self, url: str, categorie: str):
        """Récupère le premier article d'une page CS2."""
        self._demarrer()

        for tentative in range(3):
            try:
                print(f"[{categorie}] Tentative {tentative+1} sur {url}")

                page = self.browser.new_page()
                page.set_extra_http_headers({"User-Agent": "Mozilla/5.0"})
                page.goto(url, timeout=90000)
                page.wait_for_selector("div[id='csgo_react_root']", timeout=30000)

                html = page.content()
                page.close()

                soup = BeautifulSoup(html, "lxml")

                articles = soup.select("div[id='csgo_react_root'] div[class*='article']")
                if not articles:
                    print(f"[{categorie}] Aucun article trouvé.")
                    return None

                article = articles[0]

                titre_tag = article.find("p")
                titre = titre_tag.get_text(strip=True) if titre_tag else "Titre inconnu"

                date_tag = article.find("div")
                date = date_tag.get_text(strip=True) if date_tag else "Date inconnue"

                bullet_points = article.find_all("li")
                resume = "\n".join(f"- {li.get_text(strip=True)}" for li in bullet_points)
                if not resume:
                    resume = "Aucun résumé disponible."

                return ArticleCS2(f"{titre} ({date})", resume, url, categorie)

            except Exception as e:
                print(f"[{categorie}] Erreur : {e}")
                time.sleep(3)

        return None

    def __del__(self):
        self._arreter()

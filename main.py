# === Importation des bibliothèques nécessaires ===
import os
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# === Constantes globales ===

BASE_URL = "https://www.counter-strike.net/news/updates?l=french"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("Le secret DISCORD_WEBHOOK_URL est manquant.")

STATE_FILE = "last_sent.txt"


# === Classe représentant un patch note ===
class PatchNote:
    def __init__(self, title: str, summary: str, link: str):
        self.title = title
        self.summary = summary
        self.link = link

    def get_id(self) -> str:
        """Génère un identifiant unique basé sur le contenu du patch (hash MD5)."""
        contenu = self.summary.strip()
        return hashlib.md5(contenu.encode("utf-8")).hexdigest()


# === Classe responsable de récupérer le dernier patch depuis le site officiel ===
class PatchFetcher:
    def fetch_latest(self) -> PatchNote | None:
        """Tente de récupérer le patch note le plus récent (3 essais max)."""
        for attempt in range(3):
            try:
                print(f"[Tentative {attempt + 1}] Chargement de la page avec Playwright...")

                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(BASE_URL, timeout=90000)
                    page.wait_for_selector("div[id='csgo_react_root'] >> div", timeout=30000)
                    html = page.content()
                    browser.close()

                soup = BeautifulSoup(html, "lxml")
                articles = soup.find_all("div", class_="-EouvmnKRMabN5fJonx-O")
                if not articles:
                    print("Aucun article trouvé.")
                    return None

                article = articles[0]
                sub_divs = article.find_all("div", recursive=False)
                if len(sub_divs) < 3:
                    print("Structure inattendue dans l'article.")
                    return None

                date = sub_divs[0].get_text(strip=True)
                content_div = sub_divs[2]
                title_tag = content_div.find("p")
                title = title_tag.get_text(strip=True) if title_tag else "Titre inconnu"

                bullet_points = content_div.find_all("li")
                summary = "\n".join(f"- {li.get_text(strip=True)}" for li in bullet_points)

                return PatchNote(title=f"{title} ({date})", summary=summary, link=BASE_URL)

            except PlaywrightTimeout:
                print(f"⏱️ Timeout lors de la tentative {attempt + 1}. Nouvelle tentative...")
                time.sleep(5)
            except Exception as e:
                print(f"❌ Erreur lors de la tentative {attempt + 1} : {e}")
                time.sleep(5)

        print("Toutes les tentatives ont échoué.")
        return None


# === Classe pour gérer l'état local du dernier patch envoyé ===
class PatchState:
    def __init__(self, filepath: str = STATE_FILE):
        self.filepath = filepath

    def already_sent(self, patch_id: str) -> bool:
        """Vérifie si ce patch a déjà été envoyé (en comparant l'ID avec le fichier local)."""
        if not os.path.exists(self.filepath):
            return False
        with open(self.filepath, "r", encoding="utf-8") as f:
            return f.read().strip() == patch_id

    def mark_sent(self, patch_id: str):
        """Enregistre l'ID du patch dans le fichier local."""
        print(f"💾 Enregistrement de l'ID dans {self.filepath}")
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(patch_id)


# === Classe pour envoyer le patch sur Discord ===
class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, patch: PatchNote):
        """Construit et envoie un message Discord avec le contenu du patch."""

        # Séparer le titre et la date si possible
        if "(" in patch.title and patch.title.endswith(")"):
            titre, date = patch.title.rsplit("(", 1)
            titre = titre.strip()
            date = date.strip(")")
        else:
            titre = patch.title
            date = ""

        # Mise en forme Markdown pour Discord
        description = f"""📅 {date}

📝 **{titre}**

{patch.summary}"""

        payload = {
            "embeds": [{
                "title": "📰 Nouvelle actualité CS2 !",
                "url": patch.link,
                "description": description[:1000],  # Discord limite à 1024 caractères
                "color": 0x58A6FF
            }]
        }

        print(f"📢 Envoi de l’actualité CS2 sur Discord : {patch.title}")
        resp = requests.post(self.webhook_url, json=payload, timeout=20)
        resp.raise_for_status()


# === Classe principale qui orchestre tout ===
class PatchBot:
    def __init__(self):
        self.fetcher = PatchFetcher()
        self.state = PatchState()
        self.notifier = DiscordNotifier(WEBHOOK_URL)

    def run(self):
        """Exécute le processus complet : récupération, vérification, envoi, enregistrement."""
        patch = self.fetcher.fetch_latest()
        if not patch:
            print("Aucune mise à jour récupérée.")
            return

        patch_id = patch.get_id()
        print(f"🧠 ID du patch : {patch_id}")

        if self.state.already_sent(patch_id):
            print("⏩ Patch déjà envoyé, on ignore.")
            return

        self.notifier.send(patch)
        self.state.mark_sent(patch_id)
        print("✅ Patch note envoyé et enregistré.")


# === Point d'entrée du script ===
if __name__ == "__main__":
    PatchBot().run()

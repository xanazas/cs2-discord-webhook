import os
import time
import requests
import hashlib
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

def get_link_id(item):
    """Génère un identifiant unique basé sur le contenu du patch."""
    contenu = item["summary"].strip()
    return hashlib.md5(contenu.encode("utf-8")).hexdigest()
# URL officielle des patch notes en français
BASE_URL = "https://www.counter-strike.net/news/updates?l=french"

# Webhook Discord (à définir dans les secrets GitHub)
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("Le secret DISCORD_WEBHOOK_URL est manquant.")

# Fichier local pour mémoriser le dernier patch envoyé
STATE_FILE = "last_sent.txt"

def fetch_latest_update():
    """Charge la page avec Playwright et extrait le dernier patch note."""
    for attempt in range(3):
        try:
            print(f"[Tentative {attempt + 1}] Chargement de la page avec Playwright...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(BASE_URL, timeout=90000)  # 90 secondes max pour charger
                page.wait_for_selector("div[id='csgo_react_root'] >> div", timeout=30000) # attend que le contenu s'affiche
                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, "lxml")

            # Recherche des blocs d'articles
            articles = soup.find_all("div", class_="-EouvmnKRMabN5fJonx-O")
            if not articles:
                print("Aucun article trouvé.")
                return None

            article = articles[0]  # On prend le plus récent
            sub_divs = article.find_all("div", recursive=False)
            if len(sub_divs) < 3:
                print("Structure inattendue dans l'article.")
                return None

            date = sub_divs[0].get_text(strip=True)
            title = sub_divs[1].get_text(strip=True)
            summary = sub_divs[2].get_text(strip=True)

            return {
                "title": f"{title} ({date})",
                "link": BASE_URL,
                "summary": summary
            }

        except PlaywrightTimeout:
            print(f"⏱️ Timeout lors de la tentative {attempt + 1}. Nouvelle tentative...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Erreur lors de la tentative {attempt + 1} : {e}")
            time.sleep(5)

    print("Toutes les tentatives ont échoué.")
    return None

def already_sent(link_id):
    """Vérifie si le patch a déjà été envoyé."""
    if not os.path.exists(STATE_FILE):
        return False
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip() == link_id

def mark_sent(link_id):
    """Enregistre l'identifiant du dernier patch envoyé."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(link_id)

def send_to_discord(item):
    """Envoie le patch note sur Discord via webhook."""
    payload = {
        "embeds": [{
            "title": item["title"],
            "url": item["link"],
            "description": item["summary"][:1000],  # Discord limite à 1024 caractères
            "color": 5814783
        }]
    }
    print(f"📢 Envoi du patch note sur Discord : {item['title']}")
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    resp.raise_for_status()

def main():
    item = fetch_latest_update()
    if not item:
        print("Aucune mise à jour récupérée.")
        return

    link_id = get_link_id(item)  # ← identifiant stable basé sur le contenu

    if already_sent(link_id):
        print("⏩ Patch déjà envoyé, on ignore.")
        return

    send_to_discord(item)
    mark_sent(link_id)
    print("✅ Patch note envoyé avec succès.")

if __name__ == "__main__":
    main()

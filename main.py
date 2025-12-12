import os
import requests
from bs4 import BeautifulSoup

# URL officielle des patch notes Counter-Strike en français
BASE_URL = "https://www.counter-strike.net/news/updates?l=french"

# Récupération de l'URL du webhook depuis le secret GitHub
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("Le secret DISCORD_WEBHOOK_URL est manquant.")

# Fichier pour mémoriser la dernière mise à jour envoyée (évite les doublons)
STATE_FILE = "last_sent.txt"

def fetch_latest_update():
    """Récupère la dernière mise à jour depuis le site officiel."""
    r = requests.get(BASE_URL, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # Sélection du premier article
    article = soup.select_one("a.article") or soup.select_one("div.newsPost")
    if not article:
        return None

    # Titre
    title_el = article.select_one(".headline, .articleTitle")
    title = title_el.get_text(strip=True) if title_el else "Mise à jour Counter-Strike"

    # Lien
    link_el = article if article.name == "a" else article.select_one("a")
    link = link_el.get("href") if link_el and link_el.has_attr("href") else BASE_URL

    # Résumé
    summary_el = article.select_one(".articleSubText, .subText, .body")
    summary = summary_el.get_text(strip=True) if summary_el else ""

    return {"title": title, "link": link, "summary": summary}

def already_sent(link_id):
    """Vérifie si la mise à jour a déjà été envoyée."""
    if not os.path.exists(STATE_FILE):
        return False
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        last = f.read().strip()
    return last == link_id

def mark_sent(link_id):
    """Enregistre l'identifiant de la dernière mise à jour envoyée."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(link_id)

def send_to_discord(item):
    """Envoie la mise à jour au webhook Discord."""
    payload = {
        "embeds": [{
            "title": item["title"],
            "url": item["link"],
            "description": item["summary"][:1000],  # limite à 1000 caractères
            "color": 5814783
        }]
    }
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    resp.raise_for_status()

def main():
    item = fetch_latest_update()
    if not item:
        print("Aucun article trouvé.")
        return

    link_id = item["link"]
    if already_sent(link_id):
        print("Déjà envoyé, on ignore.")
        return

    send_to_discord(item)
    mark_sent(link_id)
    print("Patch note envoyé sur Discord.")

if __name__ == "__main__":
    main()

import os
import requests
from bs4 import BeautifulSoup

# URL du site officiel en français
BASE_URL = "https://www.counter-strike.net/news/updates?l=french"

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("DISCORD_WEBHOOK_URL manquant (secret GitHub requis).")

# Fichier pour mémoriser la dernière publication envoyée (évite les doublons)
STATE_FILE = "last_sent.txt"

def fetch_latest_update():
    # Charge la page des patch notes en FR
    r = requests.get(BASE_URL, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # Sélectionne le premier article (le plus récent)
    # Les pages Valve ont souvent une liste d'articles; on récupère titre, lien, extrait.
    article = soup.select_one("a.article") or soup.select_one("div.newsPost")
    if not article:
        return None

    # Récupération robuste du titre et du lien
    title_el = article.select_one(".headline, .articleTitle")
    title = (title_el.get_text(strip=True) if title_el else "Mise à jour Counter-Strike")
    link_el = article if article.name == "a" else article.select_one("a")
    link = link_el.get("href") if link_el and link_el.has_attr("href") else BASE_URL

    # Petit extrait (facultatif)
    summary_el = article.select_one(".articleSubText, .subText, .body")
    summary = summary_el.get_text(strip=True) if summary_el else ""

    return {"title": title, "link": link, "summary": summary}

def already_sent(link_id):
    if not os.path.exists(STATE_FILE):
        return False
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        last = f.read().strip()
    return last == link_id

def mark_sent(link_id):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(link_id)

def send_to_discord(item):
    content = f"📰 Patch Note CS2 (FR) : **{item['title']}**\n{item['summary']}\n🔗 {item['link']}"
    payload = {"content": content}
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    resp.raise_for_status()

def main():
    item = fetch_latest_update()
    if not item:
        print("Aucun article détecté.")
        return

    # Utilise le lien comme identifiant unique
    link_id = item["link"]
    if already_sent(link_id):
        print("Déjà envoyé, on ignore.")
        return

    send_to_discord(item)
    mark_sent(link_id)
    print("Envoyé à Discord.")

if __name__ == "__main__":
    main()

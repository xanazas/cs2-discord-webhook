import os
import time
import requests
from bs4 import BeautifulSoup

# URL officielle des patch notes Counter-Strike en français
BASE_URL = "https://www.counter-strike.net/news/updates"

# Récupération de l'URL du webhook depuis le secret GitHub
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("Le secret DISCORD_WEBHOOK_URL est manquant.")

# Fichier pour mémoriser la dernière mise à jour envoyée (évite les doublons)
STATE_FILE = "last_sent.txt"

def fetch_latest_update():
    """Récupère la dernière mise à jour depuis le site officiel avec retry."""
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(3):
        try:
            print(f"[Tentative {attempt + 1}] Récupération des patch notes...")
            r = requests.get(BASE_URL, headers=headers, timeout=120)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            # Trouver tous les blocs d'article
            articles = soup.find_all("div", class_="-EouvmnKRMabN5fJonx-O")
            if not articles:
                print("Aucun article trouvé.")
                return None

            article = articles[0]  # Le plus récent

            # Récupérer les 3 sous-divs (date, titre, contenu)
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

        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la tentative {attempt + 1}: {e}")
            time.sleep(5)

    print("Toutes les tentatives ont échoué.")
    return None

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
    print(f"Envoi du patch note sur Discord : {item['title']} ({item['link']})")
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    resp.raise_for_status()

def main():
    item = fetch_latest_update()
    if not item:
        print("Aucune mise à jour récupérée.")
        return

    link_id = item["title"]  # Utilise le titre comme identifiant unique
    if already_sent(link_id):
        print("Mise à jour déjà envoyée, on ignore.")
        return

    send_to_discord(item)
    mark_sent(link_id)
    print("✅ Patch note envoyé avec succès sur Discord.")

if __name__ == "__main__":
    main()

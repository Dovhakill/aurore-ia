import os
import json
import requests
import sys

# --- Configuration ---
# À récupérer depuis les secrets/variables d'environnement d'Aurore
GITHUB_TOKEN = os.environ.get("GH_PAT_AURORE")
REPO_OWNER = "Dovhakill" 
REPO_NAME = "horizon-libre-site"      

def trigger_autotweet_workflow(new_article_paths: list[str]):
    """
    Déclenche le workflow "Aurore - Auto Tweet" via un événement repository_dispatch.
    """
    if not GITHUB_TOKEN:
        print("Erreur: Le secret GH_PAT_AURORE est manquant.", file=sys.stderr)
        sys.exit(1)

    if not new_article_paths:
        print("Info: Aucun nouvel article à signaler. Aucune action.")
        return

    # L'URL de l'API GitHub pour les événements repository_dispatch
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/dispatches"

    # Les données à envoyer. Le workflow y accédera via `github.event.client_payload.articles`
    payload = {
        "event_type": "new-article-published",
        "client_payload": {
            "articles": new_article_paths
        }
    }

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}"
    }

    print(f"Envoi de l'événement 'new-article-published' pour: {new_article_paths}")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
        response.raise_for_status() # Lève une exception si le statut est 4xx ou 5xx
        print(f"Succès ! Événement envoyé. Réponse: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de l'envoi de l'événement à GitHub: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Détails de la réponse: {e.response.text}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Aurore devra appeler ce script en passant les chemins des fichiers en arguments.
    # Exemple: python trigger_autotweet.py article/a.html article/b.html
    if len(sys.argv) > 1:
        # Les arguments sont les chemins des nouveaux articles
        files_to_tweet = sys.argv[1:]
        trigger_autotweet_workflow(files_to_tweet)
    else:
        print("Usage: python trigger_autotweet.py <chemin/article1.html> [<chemin/article2.html> ...]")
        print("Utilisation d'un exemple car aucun argument n'a été fourni.")
        example_files = ["article/2025-08-20-exemple-dispatch.html"]
        trigger_autotweet_workflow(example_files)


import argparse
import os
import json
import datetime
from dotenv import load_dotenv

# On importe tous nos modules spécialisés
from . import news_fetch
from . import summarize
from . import github_pr
from . import dedup
from . import image_search
from . import autotweet

def main():
       # BLOC DE DÉBOGAGE DES SECRETS
    print("--- VÉRIFICATION DES SECRETS DANS L'ENVIRONNEMENT ---")
    secrets_to_check = [
        "GNEWS_API_KEY", "GEMINI_API_KEY", "GITHUB_TOKEN",
        "NETLIFY_BLOBS_TOKEN", "NETLIFY_SITE_ID", "TWITTER_API_KEY",
        "TWITTER_API_SECRET_KEY", "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET", "TWITTER_BEARER_TOKEN"
    ]
    for secret in secrets_to_check:
        if os.getenv(secret):
            print(f"[✅] {secret} : Trouvé.")
        else:
            print(f"[❌] {secret} : MANQUANT.")
    print("----------------------------------------------------")
    # FIN DU BLOC DE DÉBOGAGE
    """Fonction principale orchestrant la génération d'un article et sa publication."""
    print(f"--- Lancement d'Aurore ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    
    # Configuration
    parser = argparse.ArgumentParser(description="Génère et publie un article pour Horizon Network.")
    parser.add_argument('--config', type=str, required=True, help='Configuration à utiliser (ex: libre ou tech)')
    args = parser.parse_args()
    
    with open('config.json', 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)[args.config]
    load_dotenv()

    # Étape 1 : Vérifier la mémoire anti-doublons
    processed_urls = dedup.get_processed_urls(CONFIG)
    
    # Étape 2 : Récupérer les dernières nouvelles
    articles = news_fetch.get_news_from_api(CONFIG)
    if not articles:
        print("Aucun article trouvé par l'API. Arrêt.")
        return

    # Étape 3 : Trouver le premier article non traité
    article_to_process = dedup.find_first_unique_article(articles, processed_urls)
    if not article_to_process:
        print("Aucun nouvel article à traiter après filtrage des doublons. Arrêt.")
        return

    # Étape 4 : Générer le résumé avec l'IA
    title, summary = summarize.summarize_article(article_to_process.get('content', ''), CONFIG)
    if not title or not summary:
        print("Échec de la génération du résumé. Arrêt.")
        return

    # Étape 5 : Extraire l'image de l'article source
    image_url = image_search.find_image_from_source(article_to_process.get('url'))
    if not image_url:
        print("Aucune image trouvée, on continue sans.")

    # Étape 6 : Publier l'article et mettre à jour l'index
    result_message, article_title, article_url = github_pr.publish_article_and_update_index(title, summary, image_url, CONFIG)

    # Étape 7 : Si la publication a réussi, mettre à jour la mémoire et tweeter
    if result_message:
        processed_urls.add(article_to_process['url'])
        dedup.save_processed_urls(processed_urls, CONFIG)
        print(f"Résultat final : {result_message}")
        
        # On tweete le nouvel article
        autotweet.post_tweet(article_title, article_url)
    
    print("--- Fin du cycle d'Aurore ---")

if __name__ == "__main__":
    main()

import argparse
import os
import json
import datetime
from dotenv import load_dotenv
from . import news_fetch, summarize, github_pr, dedup, image_search

def main():
    print(f"--- Lancement d'Aurore ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    parser = argparse.ArgumentParser(description="Génère un article pour Horizon.")
    parser.add_argument('--config', type=str, required=True, help='Configuration à utiliser')
    args = parser.parse_args()

    with open('config.json', 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)[args.config]
    load_dotenv()

    processed_urls = dedup.get_processed_urls(CONFIG)
    articles = news_fetch.get_news_from_api(CONFIG)
    if not articles:
        print("Aucun article trouvé. Arrêt.")
        return

    article_to_process = dedup.find_first_unique_article(articles, processed_urls)
    if not article_to_process:
        print("Aucun nouvel article à traiter. Arrêt.")
        return

    title, summary = summarize.summarize_article(article_to_process.get('content', ''), CONFIG)
    if not title or not summary:
        print("Échec de la génération du résumé. Arrêt.")
        return

    # CORRECTION : On passe l'URL de l'article source à la fonction de recherche d'image
    image_url = image_search.find_image(article_to_process.get('url'))

    # Si aucune image n'est trouvée, on continue sans (le template gère ce cas)
    if not image_url:
        print("On continue sans image principale.")

    result = github_pr.publish_article_and_update_index(title, summary, image_url, CONFIG)

    if result:
        processed_urls.add(article_to_process['url'])
        dedup.save_processed_urls(processed_urls, CONFIG)
        print(f"Résultat final : {result}")

    print("--- Fin du cycle d'Aurore ---")

if __name__ == "__main__":
    main()

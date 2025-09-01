# -*- coding: utf-8 -*-
import os
import sys
import json
import argparse
import datetime
from dotenv import load_dotenv
from . import news_fetch, summarize, github_pr, dedup, image_search, autotweet

def main():
    """Fonction principale orchestrant la génération d'un article et sa publication."""
    print(f"--- Lancement d'Aurore ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    
    # Configuration
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True, help="Nom de la configuration à utiliser (ex: libre)")
    args = parser.parse_args()
    
    with open('config.json', 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)[args.config]
    
    load_dotenv()

    # 1. Déduplication
    processed_urls = dedup.get_processed_urls(CONFIG)
    articles = news_fetch.get_news_from_api(CONFIG)
    if not articles:
        print("Aucun article trouvé par l'API. Arrêt.")
        return

    article_to_process = dedup.find_first_unique_article(articles, processed_urls)
    if not article_to_process:
        print("Aucun nouvel article à traiter. Arrêt.")
        return

    # 2. Résumé
    title, summary = summarize.summarize_article(article_to_process.get('content', ''), CONFIG)
    if not title or not summary:
        print("Échec de la génération du résumé. Arrêt.")
        return

    # 3. Recherche d'image
    image_url = image_search.find_image_from_source(article_to_process.get('url'))

    # 4. Publication
    result_message, article_title, article_url = github_pr.publish_article_and_update_index(title, summary, image_url, CONFIG)

    # 5. Post-publication
    if result_message:
        # Sauvegarde en mémoire
        processed_urls.add(article_to_process['url'])
        dedup.save_processed_urls(processed_urls, CONFIG)
        print(f"Résultat final : {result_message}")
        
        # Tweet
        autotweet.post_tweet(article_title, summary, article_url, CONFIG)

    print("--- Fin du cycle d'Aurore ---")

if __name__ == "__main__":
    main()

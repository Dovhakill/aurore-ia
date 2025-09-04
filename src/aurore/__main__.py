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
    print(f"--- Lancement d'Aurore ({datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}) ---")
    
    # Configuration
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True, help="Nom de la configuration à utiliser (ex: libre)")
    args = parser.parse_args()

    load_dotenv()
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            configs = json.load(f)
    except Exception as e:
        print(f"Erreur critique : Impossible de charger config.json : {e}")
        sys.exit(1)

    if args.config not in configs:
        print(f"Erreur : configuration '{args.config}' introuvable dans config.json.")
        sys.exit(1)

    CONFIG = configs[args.config]
    print(f"Configuration active : {args.config} ({CONFIG.get('brand_name', 'N/A')})")

    # 1. Déduplication (lecture mémoire legacy + clés par article lors du marquage)
    processed_urls = dedup.get_processed_urls(CONFIG)

    # 2. Récupération des articles via GNews
    articles = news_fetch.get_news_from_api(CONFIG)
    if not articles:
        print("Aucun article trouvé par l'API. Arrêt.")
        return

    article_to_process = dedup.find_first_unique_article(articles, processed_urls)
    if not article_to_process:
        print("Aucun nouvel article à traiter. Arrêt.")
        return

    # 3. Résumé (Gemini)
    title, summary = summarize.summarize_article(article_to_process.get('content', ''), CONFIG)
    if not title or not summary:
        print("Échec de la génération du résumé. Arrêt.")
        return

    # 4. Image (optionnelle selon config)
    image_url = None
    if CONFIG.get('extract_image', False):
        image_url = image_search.find_image_from_source(article_to_process.get('url'))

    # 5. Publication (article + index)
    result_message, article_title, article_url = github_pr.publish_article_and_update_index(
        title, summary, image_url, CONFIG, published_at=article_to_process.get('publishedAt')
    )

    # 6. Post-publication
    if result_message:
        # Marquage en mémoire (nouveau schéma par clé) + legacy (liste)
        dedup.mark_processed(article_to_process['url'], article_to_process.get('publishedAt'), CONFIG)
        processed_urls.add(article_to_process['url'])
        dedup.save_processed_urls(processed_urls, CONFIG)
        print(f"Résultat final : {result_message}")
        
        # Tweet
        autotweet.post_tweet(article_title, summary, article_url, CONFIG)

    print("--- Fin du cycle d'Aurore ---")

if __name__ == "__main__":
    main()

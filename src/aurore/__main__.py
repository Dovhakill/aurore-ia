# CODE FINAL POUR __main__.py
import argparse, os, json, datetime
from dotenv import load_dotenv
from . import news_fetch, summarize, github_pr, dedup, image_search, autotweet

def main():
    print(f"--- Lancement d'Aurore ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True)
    args = parser.parse_args()
    
    with open('config.json', 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)[args.config]
    load_dotenv()

    # ... (toute la logique de fetch, dedup, summarize, find_image reste la même)
    
    result_message, article_title, article_url = github_pr.publish_article_and_update_index(title, summary, image_url, CONFIG)

    if result_message:
        processed_urls.add(article_to_process['url'])
        dedup.save_processed_urls(processed_urls, CONFIG)
        print(f"Résultat final : {result_message}")
        
        # On tweete l'article
        autotweet.post_tweet(article_title, article_url)

    print("--- Fin du cycle d'Aurore ---")

if __name__ == "__main__":
    main()

import argparse
import os
import json
from dotenv import load_dotenv

from . import news_fetch
from . import summarize
from . import github_pr
from . import dedup

def load_app_config(config_name):
    """Charge la configuration spécifiée (libre ou tech) depuis config.json."""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            configs = json.load(f)
        if config_name not in configs:
            raise ValueError(f"Configuration '{config_name}' non trouvée dans config.json")
        print(f"Configuration '{config_name}' chargée avec succès.")
        return configs[config_name]
    except FileNotFoundError:
        print("Erreur : Le fichier 'config.json' est introuvable.")
        exit(1)
    except json.JSONDecodeError:
        print("Erreur : Le fichier 'config.json' est mal formaté.")
        exit(1)

def main():
    """Fonction principale orchestrant la génération d'un article."""
    print(f"--- Lancement d'Aurore ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    
    parser = argparse.ArgumentParser(description="Génère un article pour Horizon.")
    parser.add_argument('--config', type=str, required=True, help='Configuration à utiliser (ex: libre ou tech)')
    args = parser.parse_args()
    
    CONFIG = load_app_config(args.config)
    load_dotenv()

    processed_urls_set = dedup.get_processed_urls(CONFIG)
    articles = news_fetch.get_news_from_api(CONFIG)

    if not articles:
        print("Aucun article trouvé par l'API. Arrêt.")
        return

    article_to_process = dedup.find_first_unique_article(articles, processed_urls_set)

    if not article_to_process:
        print("Aucun nouvel article à traiter après filtrage des doublons. Arrêt.")
        return

    title, summary_markdown = summarize.summarize_article(
        article_content=article_to_process.get('content', ''),
        config=CONFIG
    )

    if not title or not summary_markdown:
        print("Échec de la génération du résumé. Arrêt.")
        return

    pr_url = github_pr.create_github_pr(
        title=title,
        summary=summary_markdown,
        image_url=article_to_process.get('urlToImage'),
        config=CONFIG
    )

    if pr_url:
        print(f"Mise à jour de la base des doublons avec l'URL : {article_to_process['url']}")
        processed_urls_set.add(article_to_process['url'])
        dedup.save_processed_urls(processed_urls_set, CONFIG)
    
    print("--- Fin du cycle d'Aurore ---")

if __name__ == "__main__":
    import datetime
    main()

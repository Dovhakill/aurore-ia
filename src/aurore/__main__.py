import argparse
import os
import json
import datetime
from dotenv import load_dotenv

from . import news_fetch
from . import summarize
from . import github_pr
from . import dedup

def load_app_config(config_name):
    # ... (cette fonction ne change pas)
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            configs = json.load(f)
        if config_name not in configs:
            raise ValueError(f"Configuration '{config_name}' non trouvée dans config.json")
        print(f"Configuration '{config_name}' chargée avec succès.")
        return configs[config_name]
    except Exception as e:
        print(f"Erreur de chargement de la config : {e}")
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

    # AJUSTEMENT : On récupère le message de succès (URL de PR ou message de publication directe)
    result_message = github_pr.create_github_pr(
        title=title,
        summary=summary_markdown,
        image_url=article_to_process.get('urlToImage'),
        config=CONFIG
    )

    if result_message:
        print(f"Mise à jour de la base des doublons avec l'URL : {article_to_process['url']}")
        processed_urls_set.add(article_to_process['url'])
        dedup.save_processed_urls(processed_urls_set, CONFIG)
        # On imprime le message de résultat final
        print(f"Résultat final : {result_message}")
    
    print("--- Fin du cycle d'Aurore ---")

if __name__ == "__main__":
    main()

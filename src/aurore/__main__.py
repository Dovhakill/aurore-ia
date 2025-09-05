# -*- coding: utf-8 -*-
import os, sys, json, argparse
from . import news_fetch, summarize, github_pr, dedup, autotweet

def _load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _select_vertical(cfg_all: dict, key: str) -> dict:
    if key not in cfg_all:
        raise KeyError(f"Clé de verticale introuvable dans config.json: '{key}'")
    v = cfg_all[key]
    v["__key__"] = key  # pour logs/tweets
    return v

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, choices=["libre", "tech"], help="Verticale à exécuter")
    ap.add_argument("--config-file", default="config.json", help="Chemin du fichier config.json")
    args = ap.parse_args()

    print("Démarrage du bot Aurore (schéma config d'origine).")
    cfg_all = _load_config(args.config_file)
    CFG = _select_vertical(cfg_all, args.config)

    # 1) Récupération news
    articles = news_fetch.get_news_from_api(CFG)
    if not articles:
        print("Aucun article brut renvoyé par GNews. Arrêt.")
        sys.exit(0)

    # 2) Mémoire anti-doublons (legacy + nouveaux hash)
    processed_legacy = dedup.get_processed_urls(CFG)
    candidate = dedup.find_first_unique_article(articles, processed_legacy)
    if not candidate:
        print("Aucun article unique — rien à publier.")
        sys.exit(0)

    # 3) Résumé via ton prompt (balises)
    title, summary = summarize.summarize_article(
        article_content=candidate["content"],
        gemini_prompt=CFG.get("gemini_prompt", "")
    )
    if not (title and summary):
        print("Résumé indisponible — abort.")
        sys.exit(0)

    # 4) Publication GitHub (article + index), tri par publishedAt ISO
    result_message, article_title, article_url = github_pr.publish_article_and_update_index(
        title=title,
        summary=summary,
        image_url=None,                  # extraction image volontairement neutre ici
        config=CFG,
        published_at=candidate.get("publishedAt")
    )
    print(result_message)

    # 5) Marquer traité
    dedup.mark_processed(candidate["url"], candidate.get("publishedAt"), CFG)

    # 6) Tweet via ton prompt
    autotweet.tweet_from_prompt(
        cfg=CFG,
        title=title,
        summary=summary,
        source_name=news_fetch.extract_source_name(candidate["url"]),
        url=article_url
    )

if __name__ == "__main__":
    main()

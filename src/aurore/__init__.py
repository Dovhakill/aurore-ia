from .config import Settings
from .news_fetch import fetch_top_fr, find_additional_sources
from .dedup import seen, mark
from .summarize import synthesize_neutral
from .render import render_article
from .github_pr import open_pr
from .utils import topic_key
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("aurore")

def run_once():
    Settings.validate()
    candidates = fetch_top_fr(page_size=20)
    
    logger.info("Nombre d'articles candidats trouvés sur GNews : %d", len(candidates))
    
    if not candidates:
        logger.info("Aucun article trouvé. Le travail est terminé pour cette fois.")
        return

    # On ne traite que le tout premier article de la liste
    first_article = candidates[0]
    title = first_article.get("title") or first_article.get("description") or ""

    if not title:
        logger.info("Le premier article n'a pas de titre. On s'arrête.")
        return

    logger.info("Tentative de traitement pour l'article : %s", title)
    
    sources = find_additional_sources(title, first_article.get("url"), max_sources=3)
    if len(sources) < 3:
        # Duplique les sources si on n'en trouve pas 3, pour que le prompt de l'IA ait la bonne structure
        sources = (sources * 3)[:3]

    key = topic_key(title, sources)
    
    if seen(key):
        logger.info("Déjà vu (skipping): %s", title)
        return

    try:
        data = synthesize_neutral(title, sources)
        art_title = data.get("title", title)
        body = data.get("body", "")
        bullets = data.get("bullets", [])
        meta = data.get("meta", {"keywords": [], "description": title[:150]})
        path, html, slug = render_article("templates", art_title, body, sources, bullets=bullets, meta=meta)
        
        pr_url = open_pr(
            repo_fullname=Settings.GH_SITE_REPO,
            token=Settings.GH_TOKEN,
            path=path,
            html=html,
            author_name=Settings.GH_AUTHOR_NAME,
            author_email=Settings.GH_AUTHOR_EMAIL,
            title=art_title
        )
        
        mark(key, {"title": art_title, "pr": pr_url, "sources": sources})
        logger.info("SUCCÈS ! PR créée : %s", pr_url)
        
    except Exception as e:
        logger.exception("Échec du traitement de l'article %s: %s", title, e)

    logger.info("Traitement du premier article terminé. Arrêt du script.")

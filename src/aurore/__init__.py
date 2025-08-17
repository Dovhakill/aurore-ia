from .config import Settings
from .news_fetch import fetch_top_fr, find_additional_sources
from .dedup import seen, mark
from .summarize import synthesize_neutral
from .render import render_article
from .github_pr import open_pr
from .utils import topic_key
from .image_search import find_unsplash_image # On importe notre nouvelle fonction
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

    first_article = candidates[0]
    title = first_article.get("title") or ""

    if not title:
        logger.info("Le premier article n'a pas de titre. On s'arrête.")
        return

    logger.info("Tentative de traitement pour l'article : %s", title)
    
    # On cherche toujours jusqu'à 3 sources
    sources = find_additional_sources(title, first_article.get("url"), max_sources=3)
    
    # MODIFICATION : On enlève la duplication et on vérifie juste qu'on a au moins une source
    if not sources:
        logger.warning("Aucune source trouvée pour l'article '%s'. Article ignoré.", title)
        return

    key = topic_key(title, sources)
    
    if seen(key):
        logger.info("Déjà vu (skipping): %s", title)
        return
# Dans la fonction run_once, dans le bloc try:
    try:
        data = synthesize_neutral(title, sources)
        art_title = data.get("title", title)
        category = data.get("category", "International") # On récupère la catégorie
        
        image_details = find_unsplash_image(art_title)
        body = data.get("body", "")
        bullets = data.get("bullets", [])
        meta = data.get("meta", {})
        dek = data.get("dek", "")
        
        # On passe la catégorie au rendu
        path, html, slug = render_article("templates", art_title, body, sources, category, bullets=bullets, meta=meta, dek=dek, image=image_details)
        
        # ... (le reste ne change pas) ...
        # On passe à Gemini la liste des sources, quel que soit leur nombre (1, 2 ou 3)
        data = synthesize_neutral(title, sources)
        
        art_title = data.get("title", title)
        image_details = find_unsplash_image(art_title)
        body = data.get("body", "")
        bullets = data.get("bullets", [])
        meta = data.get("meta", {})
        dek = data.get("dek", "")
        
        path, html, slug = render_article("templates", art_title, body, sources, bullets=bullets, meta=meta, dek=dek, image=image_details)
        
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
    
    sources = find_additional_sources(title, first_article.get("url"), max_sources=3)
    if len(sources) < 3:
        sources = (sources * 3)[:3]

    key = topic_key(title, sources)
    
    if seen(key):
        logger.info("Déjà vu (skipping): %s", title)
        return

    try:
        data = synthesize_neutral(title, sources)
        art_title = data.get("title", title)
        
        # On cherche une image après avoir le titre final de l'IA
        image_details = find_unsplash_image(art_title)

        body = data.get("body", "")
        bullets = data.get("bullets", [])
        meta = data.get("meta", {})
        dek = data.get("dek", "")
        
        # On passe les détails de l'image au rendu
        path, html, slug = render_article("templates", art_title, body, sources, bullets=bullets, meta=meta, dek=dek, image=image_details)
        
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

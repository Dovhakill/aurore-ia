from .config import Settings
from .news_fetch import fetch_top_fr, find_additional_sources
from .dedup import seen, mark
from .summarize import synthesize_neutral
from .render import render_article
from .github_pr import open_pr
from .utils import topic_key, canonical_slug
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aurore")

def run_once():
    Settings.validate()
    candidates = fetch_top_fr(page_size=20)
    created = 0

    for art in candidates:
        title = art.get("title") or art.get("description") or ""
        if not title:
            continue
        sources = find_additional_sources(title, art.get("url"), max_sources=3)
        if len(sources) < 1:
            continue
        if len(sources) < 3:
            sources = (sources * 3)[:3]

        key = topic_key(title, sources)
        if seen(key):
            logger.info("Déjà vu (skipping): %s", title)
            continue

        try:
            data = synthesize_neutral(title, sources)
            art_title = data.get("title", title)
            body = data.get("body", f"<p>Contenu non généré pour {title}.</p>")
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
            logger.info("Created PR: %s", pr_url)
            created += 1
        except Exception as e:
            logger.exception("Erreur traitement article %s: %s", title, e)

        if created >= Settings.MAX_ARTICLES_PER_RUN:
            break
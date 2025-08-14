# Fichier : aurore-ia/src/aurore/render.py

import datetime as dt
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .utils import canonical_slug

def render_article(tpl_dir: str, title: str, body_html: str, sources: list[str], bullets=None, meta=None, dek=None):
    env = Environment(
        loader=FileSystemLoader(tpl_dir),
        autoescape=select_autoescape(["html", "xml"])
    )
    tpl = env.get_template("article.html.j2")
    now = dt.datetime.utcnow()
    slug = canonical_slug(title)
    
    html = tpl.render(
        title=title,
        published_iso=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        body=body_html,
        sources=sources,
        bullets=bullets or [],
        meta=meta or {},
        slug=slug,
        dek=dek or ""
    )
    
    # MODIFICATION : On change le chemin du dossier ici
    path = f"article/{slug}.html"
    
    return path, html, slug

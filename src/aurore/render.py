import datetime as dt
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .utils import canonical_slug
import locale

# Définit la langue française pour les dates
locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

def render_article(tpl_dir: str, title: str, body_html: str, sources: list[str], bullets=None, meta=None, dek=None, image=None):
    env = Environment(loader=FileSystemLoader(tpl_dir), autoescape=select_autoescape(["html", "xml"]))
    tpl = env.get_template("article.html.j2")
    now = dt.datetime.utcnow()
    slug = canonical_slug(title)
    
    html = tpl.render(
        title=title,
        published_iso=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        # On ajoute la date formatée pour les humains
        published_human=now.strftime("%d %B %Y"),
        body=body_html,
        sources=sources,
        bullets=bullets or [],
        meta=meta or {},
        slug=slug,
        dek=dek or "",
        image=image
    )
    
    path = f"article/{slug}.html"
    return path, html, slug

import datetime as dt
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .utils import canonical_slug
import locale

try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, '')

def render_article(tpl_dir: str, title: str, body_html: str, sources: list[str], category: str, bullets=None, meta=None, dek=None, image=None):
    env = Environment(loader=FileSystemLoader(tpl_dir), autoescape=select_autoescape(["html", "xml"]))
    tpl = env.get_template("article.html.j2")
    now = dt.datetime.now(dt.timezone.utc)
    slug = canonical_slug(title)
    
    html = tpl.render(
        title=title,
        published_iso=now.isoformat(),
        published_human=now.strftime("%d %B %Y"),
        body=body_html,
        sources=sources,
        category=category or "International", # On passe la catégorie
        bullets=bullets or [],
        meta=meta or {},
        slug=slug,
        dek=dek or "",
        image=image
    )
    
    path = f"article/{slug}.html"
    return path, html, slug

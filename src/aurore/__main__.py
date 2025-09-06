# src/aurore/__main__.py
from __future__ import annotations

import os
import sys
import re
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Optional, Tuple

# Libs tierces (présentes dans requirements.txt)
from github import Github, Auth
from bs4 import BeautifulSoup  # beautifulsoup4
from jinja2 import Environment, FileSystemLoader, select_autoescape
from gnews import GNews

# Tweepy facultatif (tweet si clés présentes)
try:
    import tweepy  # type: ignore
except Exception:
    tweepy = None  # pas de hard fail si non installé

# -----------------------------
# Utilitaires
# -----------------------------
def log(msg: str) -> None:
    print(msg, flush=True)

def getenv_any(*names: str) -> Optional[str]:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None

def slugify(text: str) -> str:
    text = text.lower().strip()
    # latin chars
    text = re.sub(r"[àáâäãå]", "a", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[èéêë]", "e", text)
    text = re.sub(r"[ìíîï]", "i", text)
    text = re.sub(r"[ñ]", "n", text)
    text = re.sub(r"[òóôöõ]", "o", text)
    text = re.sub(r"[ùúûü]", "u", text)
    text = re.sub(r"[ýÿ]", "y", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# -----------------------------
# Contexte / Config site
# -----------------------------
def site_config(site: str) -> dict:
    site = (site or "tech").strip().lower()
    if site not in {"tech", "libre"}:
        site = "tech"

    # NOTE: adapter ici si les noms de repos changent
    repo_map = {
        "tech":  "Dovhakill/horizon-tech-site",
        "libre": "Dovhakill/horizon-libre-site",
    }
    topic_map = {
        "tech":  "technology",
        "libre": "technology",  # on reste sur tech, mais filtres éditoriaux côté code
    }
    brand_map = {
        "tech":  "Horizon Tech",
        "libre": "Horizon Libre",
    }

    return {
        "key": site,
        "brand": brand_map[site],
        "repo": repo_map[site],
        "topic": topic_map[site],
        "index_selector": "#latest-articles",
        "index_keep": 10,
        "articles_dir": "articles",
        "templates_dir": "templates",
        "article_tpl": "article.html.j2",  # fallback si absent
    }

# -----------------------------
# GitHub
# -----------------------------
def gh_client() -> Github:
    # priorité aux secrets que tu utilises réellement
    token = getenv_any("A_GH_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "Aucun token GitHub trouvé (A_GH_TOKEN / GH_TOKEN / GITHUB_TOKEN)."
        )
    # Auth.Token supprime le warning ‘login_or_token is deprecated’
    return Github(auth=Auth.Token(token))

def gh_get_file(repo, path: str) -> Tuple[Optional[object], Optional[str]]:
    """Retourne (ContentFile | None, sha | None)"""
    try:
        f = repo.get_contents(path)
        return f, getattr(f, "sha", None)
    except Exception:
        return None, None

def gh_put_file(repo, path: str, content: bytes, message: str) -> None:
    existing, sha = gh_get_file(repo, path)
    if existing and sha:
        repo.update_file(path, message, content, sha)
    else:
        repo.create_file(path, message, content)

# -----------------------------
# Templating
# -----------------------------
def env_jinja(templates_dir: str) -> Environment:
    return Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

def render_article_html(cfg: dict, item: dict) -> str:
    """
    item: dict avec au minimum: title, url, published, summary (optionnel)
    """
    tpl_dir = cfg["templates_dir"]
    tpl_name = cfg["article_tpl"]
    env = env_jinja(tpl_dir)

    # Fallback si le template n'existe pas
    try:
        tpl = env.get_template(tpl_name)
        return tpl.render(
            site_name=cfg["brand"],
            title=item["title"],
            url=item.get("url"),
            published=item.get("published"),
            summary=item.get("summary"),
            content=item.get("content") or item.get("summary") or "",
            author=item.get("publisher", {}).get("title") if item.get("publisher") else None,
            created_at=now_iso(),
        )
    except Exception:
        # HTML minimaliste si pas de template Jinja
        body = item.get("content") or item.get("summary") or ""
        url = item.get("url", "#")
        pub = item.get("published", "")
        return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>{item['title']} – {cfg['brand']}</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body>
  <main>
    <article>
      <h1>{item['title']}</h1>
      <p><em>Publié: {pub}</em></p>
      <p>Source: <a href="{url}" rel="noopener noreferrer">{url}</a></p>
      <hr/>
      {body}
    </article>
  </main>
</body>
</html>"""

# -----------------------------
# Ingestion news (GNews)
# -----------------------------
def fetch_candidates(cfg: dict, max_n: int = 12) -> list[dict]:
    g = GNews(language="fr", country="FR", max_results=max_n)
    # topic générique; tu peux affiner par site si besoin
    try:
        news = g.get_news_by_topic(cfg["topic"])
    except Exception:
        news = g.get_top_news()
    return news or []

def pick_latest_uncrawled(cands: list[dict]) -> Optional[dict]:
    if not cands:
        return None
    # tri par date si dispo
    def key(x):
        # GNews retourne 'published date' str; on hache pour fallback
        ts = x.get("published date") or x.get("published")
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except Exception:
            # petit fallback
            return int(hashlib.md5((x.get("title","")+x.get("url","")).encode()).hexdigest(), 16) % (10**6)
    cands = sorted(cands, key=key, reverse=True)
    return cands[0]

# -----------------------------
# Index patch
# -----------------------------
def patch_index_html(html: str, cfg: dict, article_path: str, title: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    sel = cfg["index_selector"]
    keep = cfg["index_keep"]

    container = soup.select_one(sel)
    if container is None:
        # fallback: on crée une liste UL
        container = soup.new_tag("ul")
        container["id"] = sel.lstrip("#")
        # essaye de l’insérer dans <main>, sinon en fin de body
        main = soup.find("main") or soup.body
        (main or soup).append(container)

    # Crée le nouvel item en tête
    li = soup.new_tag("li")
    a = soup.new_tag("a", href=f"/{article_path}")
    a.string = title
    li.append(a)
    container.insert(0, li)

    # Trim
    items = container.find_all("li")
    for i in items[keep:]:
        i.decompose()

    return str(soup)

# -----------------------------
# Tweet (optionnel)
# -----------------------------
def maybe_tweet(title: str, url: str) -> None:
    api_key = getenv_any("TWITTER_API_KEY")
    api_secret = getenv_any("TWITTER_API_SECRET", "TWITTER_API_SECRET_KEY")
    access_token = getenv_any("TWITTER_ACCESS_TOKEN")
    access_secret = getenv_any("TWITTER_ACCESS_SECRET", "TWITTER_ACCESS_TOKEN_SECRET")

    if not (api_key and api_secret and access_token and access_secret and tweepy):
        log("Clés Twitter manquantes — tweet ignoré.")
        return

    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )
        status = f"{title} {url}"
        client.create_tweet(text=status[:280])
        log("Tweet publié.")
    except Exception as e:
        log(f"Tweet échoué: {e}")

# -----------------------------
# MAIN
# -----------------------------
def main() -> int:
    # Mode/Contexte
    site_env = os.getenv("SITE", "tech")
    cfg = site_config(site_env)

    # Lecture de config.json (optionnel, si tu l’utilises pour d’autres réglages)
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            _ = json.load(f)
        log("Démarrage du bot Aurore (mode SAFE index).")
    except Exception:
        log("Démarrage du bot Aurore (mode SAFE index). (config.json introuvable/ignoré)")

    # 1) Collecte
    try:
        cands = fetch_candidates(cfg, max_n=12)
        log(f"{len(cands)} bruts collectés.")
    except Exception as e:
        log(f"Erreur collecte news: {e}")
        cands = []

    # Ancienne mémoire (non branchée ici)
    log("Legacy mémoire: 0 URLs")

    # 2) Sélection
    log("Sélection du plus récent non traité…")
    item = pick_latest_uncrawled(cands)
    if not item:
        log("Aucun article publiable après filtrage.")
        return 0

    title = item.get("title", "Sans titre").strip()
    url = item.get("url", "")
    published = item.get("published date") or item.get("published") or now_iso()
    log(f"Choisi: {title}\nURL: {url} — Date: {published}")

    # 3) Prépare contenu (summary très simple si pas d’IA branchée ici)
    # (Tu peux brancher ton module summarize ici si tu préfères)
    item_out = {
        "title": title,
        "url": url,
        "published": published,
        "summary": item.get("description") or item.get("content") or "",
        "publisher": item.get("publisher"),
    }

    # 4) Render HTML
    html = render_article_html(cfg, item_out)

    # 5) Publication GitHub
    gh = gh_client()
    repo = gh.get_repo(cfg["repo"])

    # path
    base_slug = slugify(title)
    slug = base_slug
    article_dir = cfg["articles_dir"].strip("/")

    # évite collision
    path = f"{article_dir}/{slug}.html"
    try:
        existing, _ = gh_get_file(repo, path)
        if existing:
            slug = f"{base_slug}-{int(time.time())}"
            path = f"{article_dir}/{slug}.html"
    except Exception:
        pass

    # commit fichier article
    gh_put_file(
        repo,
        path,
        html.encode("utf-8"),
        message=f"chore(aurore): publier article: {title}",
    )
    log(f"Publication article → {cfg['repo']}:{path}")

    # 6) Patch index.html (#latest-articles)
    try:
        # on suppose que le fichier racine s’appelle index.html
        idx_file, idx_sha = gh_get_file(repo, "index.html")
        if idx_file and getattr(idx_file, "decoded_content", None):
            idx_html = idx_file.decoded_content.decode("utf-8", errors="replace")
        else:
            idx_html = "<!doctype html><html><body><main><ul id='latest-articles'></ul></main></body></html>"

        updated = patch_index_html(idx_html, cfg, path, title)
        if idx_sha:
            repo.update_file("index.html", "chore(aurore): maj index", updated.encode("utf-8"), idx_sha)
        else:
            repo.create_file("index.html", "chore(aurore): créer index", updated.encode("utf-8"))
        log(f"Index: patch OK via sélecteur '{cfg['index_selector']}' (keep={cfg['index_keep']}).")
    except Exception as e:
        log(f"Index: patch ignoré ({e}).")

    # 7) Tweet (optionnel)
    try:
        # L’URL publique finale de l’article — ici on publie un lien relatif
        # Si tu as l’URL de prod, remplace par l’URL canonique
        public_url = f"/{path}"
        maybe_tweet(title, public_url)
    except Exception as e:
        log(f"Tweet: ignoré ({e}).")

    log("OK – Run terminé (SAFE).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        # fail visible dans les logs Actions
        log(f"Erreur fatale:

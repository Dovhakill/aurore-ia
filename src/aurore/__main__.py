# -*- coding: utf-8 -*-
import os
import sys
import json
import base64
import re
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict

from github import Github, Auth
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Dépendances optionnelles (on gère l'absence proprement)
try:
    import tweepy
except Exception:
    tweepy = None

try:
    from gnews import GNews
except Exception:
    GNews = None

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None


# -----------------------------
# Utils
# -----------------------------
def log(msg: str, level: str = "info"):
    prefix = {
        "info": "",
        "ok": "OK – ",
        "warn": "⚠️  ",
        "error": "❌ ",
    }.get(level, "")
    print(f"{prefix}{msg}")


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.environ.get(name)
    return val if val not in (None, "", "null", "None") else default


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:90]  # garde court pour les chemins


def load_config(path: str = "config.json") -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def jinja_env() -> Environment:
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


# -----------------------------
# GitHub helpers
# -----------------------------
def get_github_client():
    token = (
        get_env("A_GH_TOKEN")
        or get_env("GH_TOKEN")
        or get_env("GITHUB_TOKEN")
    )
    if not token:
        raise RuntimeError("Aucun token GitHub (A_GH_TOKEN / GH_TOKEN / GITHUB_TOKEN).")
    return Github(auth=Auth.Token(token))


def get_repo_for_site(site: str):
    if site == "tech":
        full = get_env("A_TECH_REPO")
    elif site == "libre":
        full = get_env("A_LIBRE_REPO")
    else:
        raise RuntimeError(f"Site inconnu: {site}")

    if not full or "/" not in full:
        raise RuntimeError(
            f"Repo pour site='{site}' introuvable. "
            f"Attendu env A_{site.upper()}_REPO sous forme owner/repo."
        )
    gh = get_github_client()
    return gh.get_repo(full), full


def gh_read_text(repo, path: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        f = repo.get_contents(path)
        content = base64.b64decode(f.content).decode("utf-8")
        return content, f.sha
    except Exception:
        return None, None


def gh_write_text(repo, path: str, text: str, message: str, sha: Optional[str] = None):
    encoded = text.encode("utf-8")
    content = base64.b64encode(encoded).decode("ascii")

    if sha:
        repo.update_file(path, message, text, sha, branch=repo.default_branch)
    else:
        repo.create_file(path, message, text, branch=repo.default_branch)


# -----------------------------
# NEWS → sélection minimale
# -----------------------------
def fetch_candidates(site: str, max_items: int = 8) -> List[Dict]:
    """Retourne une petite liste d’items (titre, url, date, source).
    Utilise GNews si dispo, sinon renvoie une liste vide -> le job sortira proprement."""
    items: List[Dict] = []
    if GNews is None:
        log("GNews indisponible (module non importé).", "warn")
        return items

    # FR, tech/crypto/IA
    g = GNews(language="fr", country="FR", period="1d", max_results=max_items)
    queries = [
        "intelligence artificielle",
        "IA",
        "crypto IA",
        "open source IA",
        "machine learning",
        "blockchain IA",
    ]
    for q in queries:
        try:
            res = g.get_news(q)
            for r in res[: max_items // len(queries) + 1]:
                title = r.get("title") or ""
                url = r.get("url") or ""
                published = r.get("published date") or r.get("published") or ""
                source = (r.get("publisher") or {}).get("title") or r.get("source") or ""
                if url and title:
                    items.append(
                        {
                            "title": title,
                            "url": url,
                            "published": published,
                            "source": source,
                        }
                    )
        except Exception:
            continue

    # dédoublonne par URL
    seen = set()
    dedup: List[Dict] = []
    for it in items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        dedup.append(it)

    return dedup[:max_items]


def choose_latest_not_posted(cands: List[Dict]) -> Optional[Dict]:
    # Ici on prend le premier (déjà filtré par fraicheur via GNews).
    return cands[0] if cands else None


# -----------------------------
# RENDERING / PATCH INDEX
# -----------------------------
def render_article_html(article: Dict) -> str:
    env = jinja_env()
    tpl = env.get_template("article.html.j2")
    return tpl.render(article=article)


def patch_index_html(index_html: str, new_entry: Dict, keep: int = 10) -> str:
    """Insère dans #latest-articles un <li><a>…</a> …</li>, max keep.
    Si BeautifulSoup n’est pas dispo, on fait un patch naïf basé sur regex."""
    href = f"/articles/{new_entry['filename']}"
    li_html = f'<li><a href="{href}">{new_entry["title"]}</a> <time datetime="{new_entry["iso_date"]}">{new_entry["date"]}</time></li>'

    if BeautifulSoup:
        soup = BeautifulSoup(index_html, "html.parser")
        ul = soup.select_one("#latest-articles")
        if not ul:
            # crée la liste si absente
            container = soup.body or soup
            new_ul = soup.new_tag("ul", id="latest-articles")
            container.insert(0, new_ul)
            ul = new_ul

        # prepend
        ul.insert(0, BeautifulSoup(li_html, "html.parser"))

        # trim
        lis = ul.find_all("li")
        for li in lis[keep:]:
            li.decompose()

        return str(soup)

    # fallback regex si BS4 absent
    pat = re.compile(r'(<ul[^>]*id="latest-articles"[^>]*>)(.*?)(</ul>)', re.S | re.I)
    m = pat.search(index_html)
    if not m:
        # injecte une UL au début du body
        index_html = re.sub(
            r"(<body[^>]*>)",
            r'\1\n<ul id="latest-articles">\n' + li_html + "\n</ul>\n",
            index_html,
            count=1,
            flags=re.I,
        )
        return index_html

    head, inner, tail = m.group(1), m.group(2), m.group(3)
    # prends les <li> existants
    existing = re.findall(r"<li>.*?</li>", inner, re.S | re.I)
    new_list = [li_html] + existing
    new_list = new_list[:keep]
    patched = head + "\n" + "\n".join(new_list) + "\n" + tail
    return index_html[: m.start()] + patched + index_html[m.end() :]


# -----------------------------
# TWITTER (optionnel)
# -----------------------------
def maybe_tweet(title: str, url: str):
    keys = {
        "api_key": get_env("TWITTER_API_KEY"),
        "api_secret": get_env("TWITTER_API_SECRET"),
        "access_token": get_env("TWITTER_ACCESS_TOKEN"),
        "access_secret": get_env("TWITTER_ACCESS_SECRET"),
    }
    if not all(keys.values()):
        log("Clés Twitter manquantes — tweet ignoré.", "warn")
        return

    if tweepy is None:
        log("tweepy indisponible — tweet ignoré.", "warn")
        return

    try:
        auth = tweepy.OAuth1UserHandler(
            keys["api_key"], keys["api_secret"], keys["access_token"], keys["access_secret"]
        )
        api = tweepy.API(auth)
        api.update_status(status=f"{title} {url}")
        log("Tweet publié.", "ok")
    except Exception as e:
        log(f"Tweet échec: {e}", "warn")


# -----------------------------
# MAIN PIPELINE
# -----------------------------
def main():
    site = get_env("SITE", "tech").strip().lower()
    print(f"  ")
    log(f"Démarrage du bot Aurore (mode SAFE index).")

    # Lecture config (juste pour valider le JSON)
    cfg = load_config()
    _ = cfg  # si on n'utilise pas tout, au moins on valide le fichier
    log("config.json OK", "ok")

    # 1) fetch cands
    cands = fetch_candidates(site, max_items=8)
    log(f"{len(cands)} bruts collectés.")

    # 2) mémoire legacy (non utilisée ici, juste info)
    log("Legacy mémoire: 0 URLs")

    # 3) sélection
    log("Sélection du plus récent non traité…")
    chosen = choose_latest_not_posted(cands)
    if not chosen:
        log("Aucun article publiable après filtrage.")
        return

    title = chosen["title"].strip()
    source_url = chosen["url"].strip()
    pub = chosen.get("published") or ""
    src = chosen.get("source") or ""
    # Slug du fichier
    slug = slugify(title)
    filename = f"{slug}.html"

    # 4) article dict pour template
    now = datetime.now(timezone.utc)
    article = {
        "title": title,
        "source_url": source_url,
        "source_name": src,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "iso_created_at": now.isoformat(),
        # Champs communs que tes templates peuvent attendre:
        "excerpt": f"Résumé rapide — {title}",
        "body": f"<p>Découvrez l’article original&nbsp;: <a href=\"{source_url}\">{title}</a>.<br>Source&nbsp;: {src or 'inconnu'}.</p>",
        "cover": None,
        "tags": ["IA", "Tech"] if site == "tech" else ["Libre", "IA"],
        "site": site,
    }

    # 5) rendu HTML
    html = render_article_html(article)

    # 6) push sur repo du site
    repo, repo_full = get_repo_for_site(site)
    article_path = f"articles/{filename}"
    log(f"Publication article → {repo_full}:{article_path}")

    old, sha = gh_read_text(repo, article_path)
    commit_msg = f"chore({site}): publication {filename}"
    gh_write_text(repo, article_path, html, commit_msg, sha=sha)

    # 7) patch index.html (prepend dans #latest-articles, keep=10)
    idx_html, idx_sha = gh_read_text(repo, "index.html")
    if idx_html:
        entry = {
            "title": title,
            "filename": filename,
            "date": now.strftime("%Y-%m-%d"),
            "iso_date": now.date().isoformat(),
        }
        new_idx = patch_index_html(idx_html, entry, keep=10)
        if new_idx != idx_html:
            gh_write_text(repo, "index.html", new_idx, f"chore({site}): index patch", sha=idx_sha)
            log("Index: patch OK via sélecteur '#latest-articles' (keep=10).", "ok")
        else:
            log("Index: aucun changement détecté.", "warn")
    else:
        log("Index: fichier index.html introuvable — patch ignoré.", "warn")

    # 8) Tweet (si clés présentes)
    maybe_tweet(title, f"https://{repo.owner.login}.github.io/{repo.name}/articles/{filename}")

    log("OK – Run terminé (SAFE).", "ok")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        log(f"Erreur fatale: {e}\n{tb}", level="error")
        sys.exit(1)

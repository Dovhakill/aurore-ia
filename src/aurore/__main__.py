# -*- coding: utf-8 -*-
"""
__main__.py – Orchestrateur Aurore (SAFE index)
- NE MODIFIE PLUS la structure d'index.html : ajoute juste un <li> si le sélecteur existe
- Si le sélecteur n'existe pas, on skip
"""

from __future__ import annotations
import os, sys, json, re
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from github import Github, GithubException
from jinja2 import Environment, BaseLoader
from bs4 import BeautifulSoup

from .news_fetch import get_news_from_api
from .summarize import summarize_article
from .selection import pick_freshest_unique

REPO_ROOT = Path(__file__).resolve().parents[2]
MEM_DIR = REPO_ROOT / "memory"
MEM_DIR.mkdir(exist_ok=True)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def detect_vertical() -> str:
    env_target = os.environ.get("TARGET") or os.environ.get("VERTICAL")
    if env_target in {"libre", "tech"}: return env_target
    job = (os.environ.get("GITHUB_JOB") or "").lower()
    return "tech" if "tech" in job else "libre"

def load_config() -> Dict[str, Any]:
    p = REPO_ROOT / "config.json"
    if not p.exists():
        print("config.json introuvable"); sys.exit(1)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Erreur de parsing config.json: {e}"); sys.exit(1)

def mem_path(vertical: str) -> Path: return MEM_DIR / f"{vertical}.json"
def load_memory(vertical: str) -> set[str]:
    p = mem_path(vertical)
    if not p.exists(): print("Legacy mémoire: 0 URLs"); return set()
    try:
        j = json.loads(p.read_text(encoding="utf-8") or "{}")
        urls = set(j.get("processed_hashes", []))
        print(f"Legacy mémoire: {len(urls)} URLs"); return urls
    except Exception:
        print("Legacy mémoire corrompue, on repart propre."); return set()

def save_memory(vertical: str, processed_hashes: set[str]) -> None:
    p = mem_path(vertical)
    p.write_text(json.dumps({"updated_at": now_iso(),
                             "processed_hashes": sorted(processed_hashes)},
                            ensure_ascii=False, indent=2), encoding="utf-8")

def slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:80] if len(s) > 80 else s

def first_env(*keys: str) -> Optional[str]:
    for k in keys:
        v = os.environ.get(k)
        if v: return v
    return None

ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{{ title|e }} – {{ site_name|e }}</title>
<meta name="description" content="{{ summary|e }}"/>
<meta name="generator" content="Aurore IA"/>
<meta property="og:type" content="article"/><meta property="og:url" content="{{ article_url }}"/>
<meta property="og:title" content="{{ title|e }}"/><meta property="og:description" content="{{ summary|e }}"/>
{% if main_image_url %}<meta property="og:image" content="{{ main_image_url }}"/>{% endif %}
<meta property="og:site_name" content="{{ site_name|e }}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:url" content="{{ article_url }}"/><meta name="twitter:title" content="{{ title|e }}"/>
<meta name="twitter:description" content="{{ summary|e }}"/>
{% if main_image_url %}<meta name="twitter:image" content="{{ main_image_url }}"/>{% endif %}
<style>
  :root { --brand: {{ brand_color }}; }
  body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;color:#0f172a}
  header{padding:16px 20px;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;gap:12px}
  header img{height:28px}
  header a{color:var(--brand);text-decoration:none;font-weight:700;font-size:18px}
  main{max-width:820px;margin:24px auto;padding:0 16px}
  h1{font-size:30px;line-height:1.2;margin:12px 0 10px}
  .meta{color:#475569;font-size:14px;margin-bottom:16px}
  .hero{margin:12px 0 20px}.hero img{width:100%;height:auto;border-radius:12px}
  article p{font-size:18px;line-height:1.6;margin:14px 0}
  footer{margin:36px 0 24px;color:#64748b;font-size:14px}
  .badge{display:inline-block;background:#eef2ff;color:#3730a3;padding:4px 8px;border-radius:999px;font-weight:600;font-size:12px}
</style>
<!-- meta: {"published_at":"{{ published_at }}","title":{{ title|tojson }},"source":{{ source|tojson }} } -->
</head><body>
  <header>{% if logo_url %}<img src="{{ logo_url }}" alt="{{ site_name|e }}"/>{% endif %}
    <a href="{{ home_url }}">{{ site_name|e }}</a></header>
  <main>
    <h1>{{ title|e }}</h1>
    <div class="meta">Publié le {{ published_human }} · Source: {{ source|e }}</div>
    {% if main_image_url %}<div class="hero"><img src="{{ main_image_url }}" alt=""/></div>{% endif %}
    <article>{% for p in summary.split("\\n") %}{% if p.strip() %}<p>{{ p.strip() }}</p>{% endif %}{% endfor %}</article>
    <footer><span class="badge">Généré par Aurore IA</span></footer>
  </main>
</body></html>"""
env = Environment(loader=BaseLoader())
def render_article_html(payload: Dict[str, Any]) -> str:
    return env.from_string(ARTICLE_TEMPLATE).render(**payload)

@dataclass
class RepoInfo:
    full_name: str
    production_url: str
    site_name: str
    brand_color: str
    logo_filename: Optional[str]

def gh_connect() -> Github:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN manquant."); sys.exit(1)
    return Github(token)

def gh_get_repo(gh: Github, full_name: str):
    try:
        return gh.get_repo(full_name)
    except GithubException as e:
        print(f"Repo introuvable: {full_name} – {e}"); sys.exit(1)

def gh_upsert_file(repo, path: str, content: str, message: str) -> None:
    try:
        existing = repo.get_contents(path)
        repo.update_file(path, message, content, existing.sha)
    except GithubException as e:
        if e.status == 404: repo.create_file(path, message, content)
        else: raise

# ---------- SAFE: on ne touche pas la structure d'index ----------
def safe_patch_index_html(current_html: str,
                          new_href: str,
                          new_title: str,
                          new_date_iso: str,
                          selector: str = "#latest-articles",
                          keep: int = 10) -> Optional[str]:
    """
    Ajoute un <li><a href=...>Titre</a><small>— YYYY-MM-DD</small></li>
    en tête de la liste ciblée par `selector`.
    - Si le sélecteur n'existe pas: retourne None (aucune écriture).
    - Ne modifie rien d'autre (head, styles, header conservés).
    """
    soup = BeautifulSoup(current_html, "html.parser")
    target = soup.select_one(selector)
    if not target:
        return None  # on ne bricole pas la page: sécurité

    # Dédup par href
    hrefs = {a["href"] for a in target.find_all("a", href=True)}
    if new_href not in hrefs:
        li = soup.new_tag("li")
        a = soup.new_tag("a", href=new_href); a.string = new_title
        small = soup.new_tag("small"); small.string = f"— {new_date_iso[:10]}"
        li.append(a); li.append(small)
        target.insert(0, li)

    # Trim
    lis = target.find_all("li")
    for li in lis[keep:]:
        li.decompose()

    return str(soup)

# ---------- Tweet ----------
def generate_tweet_via_gemini(title: str, summary: str, tweet_prompt: str) -> Optional[str]:
    try:
        import google.generativeai as genai
        key = os.environ.get("GEMINI_API_KEY")
        if not key: return None
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash",
            generation_config={"temperature":0.4,"top_p":0.95,"max_output_tokens":200,"response_mime_type":"text/plain"})
        resp = model.generate_content(f"{tweet_prompt}\n\n<TITRE>{title}</TITRE>\n<RESUME>{summary}</RESUME>")
        text = (getattr(resp, "text", "") or "").strip().replace("\n", " ")
        return (text[:280]).strip() or None
    except Exception as e:
        print(f"WARN tweet Gemini: {e}"); return None

def send_tweet_if_possible(text: str) -> None:
    try:
        import tweepy
    except Exception:
        print("tweepy non installé — tweet ignoré."); return
    api_key = first_env("CONSUMER_KEY","TWITTER_API_KEY")
    api_secret = first_env("CONSUMER_SECRET","TWITTER_API_SECRET")
    access_token = os.environ.get("ACCESS_TOKEN")
    access_secret = os.environ.get("ACCESS_TOKEN_SECRET")
    if not all([api_key, api_secret, access_token, access_secret]):
        print("Clés Twitter manquantes — tweet ignoré."); return
    try:
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        api = tweepy.API(auth); api.verify_credentials(); api.update_status(status=text)
        print("Tweet publié.")
    except Exception as e:
        print(f"WARN tweet échec: {e}")

# ---------- Main ----------
def main():
    print("Démarrage du bot Aurore (mode SAFE index).")
    cfg = load_config()
    vertical = detect_vertical()
    if vertical not in cfg:
        print(f"Verticale '{vertical}' absente de config.json"); sys.exit(1)
    v = cfg[vertical]

    site_repo   = v["site_repo_name"]
    production  = v["production_url"].rstrip("/")
    site_name   = v.get("brand_name", vertical.title())
    brand_color = v.get("brand_color", "#111827")
    logo_fn     = v.get("logo_filename")

    raw = get_news_from_api(v)
    print(f"{len(raw)} bruts collectés.")
    seen = load_memory(vertical)

    print("Sélection du plus récent non traité…")
    chosen = pick_freshest_unique(raw, seen)
    if not chosen:
        print("Aucun article publiable après filtrage."); sys.exit(0)
    article, article_hash = chosen
    print(f"Choisi: {article.get('title') or '[sans titre]'}")
    print(f"URL: {article['url']} — Date: {article['publishedAt']}")

    title, summary = summarize_article(article["content"], v["gemini_prompt"])
    if not (title and summary):
        print("Résumé non exploitable."); sys.exit(0)

    slug = slugify(title) or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rel_path = f"articles/{slug}.html"
    url = f"{production}/{rel_path}"
    published_iso = article["publishedAt"]

    html = render_article_html({
        "title": title,
        "summary": summary,
        "published_at": published_iso,
        "published_human": published_iso.replace("T"," ").replace("+00:00"," UTC"),
        "source": article.get("source") or "",
        "main_image_url": None,
        "site_name": site_name, "home_url": production, "article_url": url,
        "brand_color": brand_color,
        "logo_url": f"/assets/{logo_fn}" if logo_fn else None,
    })

    gh = gh_connect()
    repo = gh_get_repo(gh, site_repo)

    print(f"Publication article → {site_repo}:{rel_path}")
    gh_upsert_file(repo, rel_path, html, f"Aurore: add article '{title}'")

    # --- SAFE INDEX UPDATE ---
    if os.environ.get("SKIP_INDEX") == "1" or v.get("skip_index") is True:
        print("Index: SKIP (config/env).")
    else:
        selector = v.get("index_selector", "#latest-articles")
        keep = int(v.get("index_keep", 10))
        try:
            idx = repo.get_contents("index.html")
            current = idx.decoded_content.decode("utf-8")
            patched = safe_patch_index_html(current, f"/{rel_path}", title, published_iso,
                                            selector=selector, keep=keep)
            if patched and patched != current:
                repo.update_file("index.html", f"Aurore: patch index ({slug})", patched, idx.sha)
                print(f"Index: patch OK via sélecteur '{selector}' (keep={keep}).")
            else:
                print(f"Index: sélecteur '{selector}' introuvable ou déjà à jour — aucune écriture.")
        except GithubException as e:
            if e.status == 404:
                print("Index inexistant — on n’en crée pas (mode SAFE).")
            else:
                raise

    seen.add(article_hash)
    save_memory(vertical, seen)

    tweet_prompt = v.get("gemini_tweet_prompt")
    if tweet_prompt:
        tw = generate_tweet_via_gemini(title, summary, tweet_prompt)
        if tw:
            link = f" {url}"
            tw = (tw if len(tw)+len(link) <= 280 else tw[: 280-len(link)-1].rstrip()+"…") + link
            send_tweet_if_possible(tw)
        else:
            print("Tweet non généré.")

    print("OK – Run terminé (SAFE).")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"Erreur fatale: {e}"); sys.exit(1)

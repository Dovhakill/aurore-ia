# -*- coding: utf-8 -*-
"""
__main__.py – Orchestrateur Aurore V1.1
- Chargement config + sélection verticale (libre/tech)
- Récupération news (gnews lib multi-version + fallback RSS)
- Sélection: plus récent non traité (dédup SHA256 d'URL normalisée)
- Résumé Gemini (prompts par verticale – liste ou string)
- Publication GitHub (article HTML + mise à jour index.html, 10 derniers)
- Mémoire legacy locale (memory/<vertical>.json)
- Tweet (optionnel) via Tweepy + prompt dédié

Dépendances: PyGithub, Jinja2, BeautifulSoup4, Tweepy (optionnel), google-generativeai
"""

from __future__ import annotations
import os
import sys
import json
import re
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional

from github import Github, GithubException
from jinja2 import Environment, BaseLoader
from bs4 import BeautifulSoup

# Modules internes (fournis)
from .news_fetch import get_news_from_api
from .summarize import summarize_article
from .selection import pick_freshest_unique, hash_url, normalize_url

# ---------- Utils basiques ----------

REPO_ROOT = Path(__file__).resolve().parents[2]
MEM_DIR = REPO_ROOT / "memory"
MEM_DIR.mkdir(exist_ok=True)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def detect_vertical() -> str:
    env_target = os.environ.get("TARGET") or os.environ.get("VERTICAL")
    if env_target in {"libre", "tech"}:
        return env_target
    job = (os.environ.get("GITHUB_JOB") or "").lower()
    if "tech" in job:
        return "tech"
    return "libre"

def load_config() -> Dict[str, Any]:
    cfg_path = REPO_ROOT / "config.json"
    if not cfg_path.exists():
        print("config.json introuvable à la racine du repo.")
        sys.exit(1)
    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg
    except Exception as e:
        print(f"Erreur de parsing config.json: {e}")
        sys.exit(1)

def mem_path(vertical: str) -> Path:
    return MEM_DIR / f"{vertical}.json"

def load_memory(vertical: str) -> set[str]:
    p = mem_path(vertical)
    if not p.exists():
        print("Legacy mémoire: 0 URLs")
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8") or "{}")
        urls = set(data.get("processed_hashes", []))
        print(f"Legacy mémoire: {len(urls)} URLs")
        return urls
    except Exception:
        print("Legacy mémoire corrompue, on repart propre.")
        return set()

def save_memory(vertical: str, processed_hashes: set[str]) -> None:
    p = mem_path(vertical)
    data = {
        "updated_at": now_iso(),
        "processed_hashes": sorted(processed_hashes),
    }
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:80] if len(s) > 80 else s

def first_env(*keys: str) -> Optional[str]:
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None

# ---------- Templating article ----------

ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>{{ title|e }} – {{ site_name|e }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="{{ summary|e }}" />
  <meta name="generator" content="Aurore IA" />

  <!-- OpenGraph -->
  <meta property="og:type" content="article" />
  <meta property="og:url" content="{{ article_url }}" />
  <meta property="og:title" content="{{ title|e }}" />
  <meta property="og:description" content="{{ summary|e }}" />
  {% if main_image_url %}<meta property="og:image" content="{{ main_image_url }}" />{% endif %}
  <meta property="og:site_name" content="{{ site_name|e }}" />

  <!-- Twitter -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:url" content="{{ article_url }}" />
  <meta name="twitter:title" content="{{ title|e }}" />
  <meta name="twitter:description" content="{{ summary|e }}" />
  {% if main_image_url %}<meta name="twitter:image" content="{{ main_image_url }}" />{% endif %}

  <style>
    :root { --brand: {{ brand_color }}; }
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin:0; color:#0f172a; }
    header { padding: 16px 20px; border-bottom: 1px solid #e5e7eb; display:flex; align-items:center; gap:12px; }
    header img { height: 28px; }
    header a { color: var(--brand); text-decoration:none; font-weight: 700; font-size: 18px; }
    main { max-width: 820px; margin: 24px auto; padding: 0 16px; }
    h1 { font-size: 30px; line-height: 1.2; margin: 12px 0 10px; }
    .meta { color:#475569; font-size: 14px; margin-bottom: 16px; }
    .hero { margin: 12px 0 20px; }
    .hero img { width:100%; height:auto; border-radius: 12px; }
    article p { font-size: 18px; line-height: 1.6; margin: 14px 0; }
    footer { margin: 36px 0 24px; color:#64748b; font-size:14px; }
    .badge { display:inline-block; background: #eef2ff; color:#3730a3; padding:4px 8px; border-radius: 999px; font-weight:600; font-size:12px; }
  </style>

  <!-- Front-matter JSON pour l'indexation -->
  <!-- meta: {"published_at": "{{ published_at }}", "title": {{ title|tojson }}, "source": {{ source|tojson }} } -->
</head>
<body>
  <header>
    {% if logo_url %}<img src="{{ logo_url }}" alt="{{ site_name|e }}"/>{% endif %}
    <a href="{{ home_url }}">{{ site_name|e }}</a>
  </header>
  <main>
    <h1>{{ title|e }}</h1>
    <div class="meta">
      Publié le {{ published_human }} · Source: {{ source|e }}
    </div>

    {% if main_image_url %}
    <div class="hero">
      <img src="{{ main_image_url }}" alt="" />
    </div>
    {% endif %}

    <article>
      {# On assume que "summary" contient 3-4 paragraphes #}
      {% for para in summary.split("\\n") %}
        {% if para.strip() %}<p>{{ para.strip() }}</p>{% endif %}
      {% endfor %}
    </article>

    <footer>
      <span class="badge">Généré par Aurore IA</span>
    </footer>
  </main>
</body>
</html>
"""

env = Environment(loader=BaseLoader())

def render_article_html(payload: Dict[str, Any]) -> str:
    tpl = env.from_string(ARTICLE_TEMPLATE)
    return tpl.render(**payload)

# ---------- GitHub publication ----------

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
        print("GITHUB_TOKEN manquant.")
        sys.exit(1)
    return Github(token)

def gh_get_repo(gh: Github, full_name: str):
    try:
        return gh.get_repo(full_name)
    except GithubException as e:
        print(f"Repo introuvable: {full_name} – {e}")
        sys.exit(1)

def gh_upsert_file(repo, path: str, content: str, message: str) -> None:
    try:
        existing = repo.get_contents(path)
        repo.update_file(path, message, content, existing.sha)
    except GithubException as e:
        if e.status == 404:
            repo.create_file(path, message, content)
        else:
            raise

def build_or_update_index_html(current_html: Optional[str],
                               home_url: str,
                               site_name: str,
                               brand_color: str,
                               logo_filename: Optional[str],
                               new_href: str,
                               new_title: str,
                               new_date_iso: str) -> str:
    # Si index absent → on crée minimal
    if not current_html:
        soup = BeautifulSoup("<!doctype html><html><head><meta charset='utf-8'><title></title></head><body></body></html>", "html.parser")
    else:
        soup = BeautifulSoup(current_html, "html.parser")

    # <head> minimal
    if not soup.head:
        soup.html.insert(0, soup.new_tag("head"))
    if not soup.body:
        soup.html.append(soup.new_tag("body"))

    # Titre
    if not soup.title:
        t = soup.new_tag("title")
        t.string = site_name
        soup.head.append(t)
    else:
        soup.title.string = site_name

    # Styles simples
    style = soup.new_tag("style")
    style.string = f""":root {{ --brand: {brand_color}; }}
body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin:0; color:#0f172a; }}
header {{ padding:16px 20px; border-bottom:1px solid #e5e7eb; display:flex; align-items:center; gap:12px; }}
header img {{ height:28px; }}
header a {{ color: var(--brand); text-decoration:none; font-weight:700; font-size:18px; }}
main {{ max-width: 860px; margin: 24px auto; padding: 0 16px; }}
h1 {{ font-size: 24px; margin: 8px 0 12px; }}
ul#latest-articles {{ list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:10px; }}
ul#latest-articles li a {{ text-decoration:none; color:#111827; }}
ul#latest-articles li small {{ color:#64748b; margin-left:8px; }}
footer {{ margin: 32px 0 24px; color:#64748b; font-size:14px; }}
"""
    # Remplace ou ajoute le style (simple)
    if soup.head.find("style"):
        soup.head.find("style").replace_with(style)
    else:
        soup.head.append(style)

    # Header
    header = soup.body.find("header")
    if not header:
        header = soup.new_tag("header")
        soup.body.insert(0, header)

    header.clear()
    if logo_filename:
        img = soup.new_tag("img", src=f"/assets/{logo_filename}", alt=site_name)
        header.append(img)
    a = soup.new_tag("a", href=home_url)
    a.string = site_name
    header.append(a)

    # Main + listing
    main = soup.body.find("main")
    if not main:
        main = soup.new_tag("main")
        soup.body.append(main)

    if not main.find("h1"):
        h1 = soup.new_tag("h1")
        h1.string = "Derniers articles"
        main.append(h1)

    ul = main.find("ul", id="latest-articles")
    if not ul:
        ul = soup.new_tag("ul", id="latest-articles")
        main.append(ul)

    # Ajout en tête en évitant doublons
    hrefs_seen = set()
    new_li = soup.new_tag("li")
    a = soup.new_tag("a", href=new_href)
    a.string = new_title
    small = soup.new_tag("small")
    small.string = f"— {new_date_iso[:10]}"
    new_li.append(a)
    new_li.append(small)

    # Dedup par href et prepend
    for li in ul.find_all("li"):
        a = li.find("a", href=True)
        if a:
            hrefs_seen.add(a["href"])
    if new_href not in hrefs_seen:
        ul.insert(0, new_li)

    # Trim à 10
    items = ul.find_all("li")
    for li in items[10:]:
        li.decompose()

    # Footer signature
    if not soup.body.find("footer"):
        f = soup.new_tag("footer")
        f.string = "Généré par Aurore IA — Horizon Network"
        soup.body.append(f)

    return str(soup)

# ---------- Tweet (optionnel) ----------

def generate_tweet_via_gemini(title: str, summary: str, tweet_prompt: str) -> Optional[str]:
    try:
        import google.generativeai as genai
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            return None
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            generation_config={"temperature": 0.4, "top_p": 0.95, "max_output_tokens": 200, "response_mime_type": "text/plain"},
        )
        prompt = f"{tweet_prompt}\n\nContexte:\n<TITRE>{title}</TITRE>\n<RESUME>{summary}</RESUME>"
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None) or ""
        text = text.strip().replace("\n", " ")
        return (text[:280]).strip() if text else None
    except Exception as e:
        print(f"WARN tweet Gemini: {e}")
        return None

def send_tweet_if_possible(text: str) -> None:
    try:
        import tweepy
    except Exception:
        print("tweepy non installé — tweet ignoré.")
        return

    api_key = first_env("CONSUMER_KEY", "TWITTER_API_KEY")
    api_secret = first_env("CONSUMER_SECRET", "TWITTER_API_SECRET")
    access_token = os.environ.get("ACCESS_TOKEN")
    access_secret = os.environ.get("ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        print("Clés Twitter manquantes — tweet ignoré.")
        return
    try:
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        api = tweepy.API(auth)
        api.verify_credentials()
        api.update_status(status=text)
        print("Tweet publié.")
    except Exception as e:
        print(f"WARN tweet échec: {e}")

# ---------- Main pipeline ----------

def main():
    print("Démarrage du bot Aurore (schéma config d'origine).")

    cfg = load_config()
    vertical = detect_vertical()
    if vertical not in cfg:
        print(f"Verticale '{vertical}' non définie dans config.json.")
        sys.exit(1)

    vcfg = cfg[vertical]
    site_repo = vcfg["site_repo_name"]
    production_url = vcfg["production_url"].rstrip("/")
    site_name = vcfg.get("brand_name", vertical.title())
    brand_color = vcfg.get("brand_color", "#111827")
    logo_filename = vcfg.get("logo_filename")

    # 1) Collecte
    raw = get_news_from_api(vcfg)
    print(f"{len(raw)} bruts collectés.")

    # 2) Mémoire
    seen = load_memory(vertical)

    # 3) Sélection
    print("Sélection du plus récent non traité…")
    chosen = pick_freshest_unique(raw, seen)
    if not chosen:
        print("Aucun article publiable après filtrage (doublons / contenu trop court).")
        sys.exit(0)

    article, article_hash = chosen
    print(f"Choisi: {article.get('title') or '[sans titre]'}")
    print(f"URL: {article['url']}")
    print(f"Date: {article['publishedAt']}")

    # 4) Résumé
    title, summary = summarize_article(article["content"], vcfg["gemini_prompt"])
    if not (title and summary):
        print("Résumé non exploitable. Abandon.")
        sys.exit(0)

    # 5) Rendu HTML
    slug = slugify(title) or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    article_rel_path = f"articles/{slug}.html"
    article_url = f"{production_url}/{article_rel_path}"
    published_iso = article["publishedAt"]

    payload = {
        "title": title,
        "summary": summary,
        "published_at": published_iso,
        "published_human": published_iso.replace("T", " ").replace("+00:00", " UTC"),
        "source": article.get("source") or "",
        "main_image_url": None,  # extract_image désactivé par défaut dans ta conf
        "site_name": site_name,
        "home_url": production_url,
        "article_url": article_url,
        "brand_color": brand_color,
        "logo_url": f"/assets/{logo_filename}" if logo_filename else None,
    }
    html = render_article_html(payload)

    # 6) Publication GitHub
    gh = gh_connect()
    repo = gh_get_repo(gh, site_repo)

    print(f"Publication article → {site_repo}:{article_rel_path}")
    gh_upsert_file(repo, article_rel_path, html, f"Aurore: add article '{title}'")

    # 7) Index update
    print("Mise à jour index.html…")
    try:
        idx = repo.get_contents("index.html")
        current_index_html = idx.decoded_content.decode("utf-8")
        new_index_html = build_or_update_index_html(
            current_index_html, production_url, site_name, brand_color, logo_filename,
            f"/{article_rel_path}", title, published_iso
        )
        repo.update_file("index.html", f"Aurore: update index with '{slug}'", new_index_html, idx.sha)
    except GithubException as e:
        if e.status == 404:
            new_index_html = build_or_update_index_html(
                None, production_url, site_name, brand_color, logo_filename,
                f"/{article_rel_path}", title, published_iso
            )
            repo.create_file("index.html", f"Aurore: create index with '{slug}'", new_index_html)
        else:
            raise

    # 8) Mémoire → on marque comme traité
    seen.add(article_hash)
    save_memory(vertical, seen)

    # 9) Tweet (optionnel)
    tweet_prompt = vcfg.get("gemini_tweet_prompt")
    if tweet_prompt:
        tweet = generate_tweet_via_gemini(title, summary, tweet_prompt)
        if tweet:
            # Ajoute le lien à la fin si ça rentre, sinon on tronque proprement
            link = f" {article_url}"
            if len(tweet) + len(link) <= 280:
                tweet += link
            else:
                tweet = tweet[: 280 - len(link) - 1].rstrip() + "…" + link
            send_tweet_if_possible(tweet)
        else:
            print("Tweet non généré (prompt/clé manquants ou échec IA).")

    print("OK – Run terminé.")

if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Erreur fatale: {e}")
        sys.exit(1)

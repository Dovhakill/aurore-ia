# -*- coding: utf-8 -*-
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from gnews import GNews

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

def extract_source_name(url: str) -> str:
    try:
        netloc = urlparse(url).netloc
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return "source"

def _to_iso(dt_like: Optional[str]) -> str:
    if not dt_like:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = parsedate_to_datetime(str(dt_like))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()

def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "aside", "form"]):
        tag.decompose()
    parts = []
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if t and len(t) >= 40:
            parts.append(t)
    text = "\n\n".join(parts)
    return text[:8000].strip()

def _fetch_article_body(url: str) -> Optional[str]:
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        text = _extract_text(r.text)
        if len(text) < 80:
            return None
        return text
    except Exception as e:
        print(f"WARN fetch échoué {url}: {e}")
        return None

def get_news_from_api(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Lit gnews_query dans ta conf, récupère et nettoie les articles."""
    query = (config.get("gnews_query") or "").strip()
    if not query:
        print("gnews_query manquant dans config de la verticale.")
        return []

    # Paramètres optionnels (si tu les ajoutes dans ta conf)
    lang = config.get("gnews_lang")  # ex: "fr" / "en"
    country = config.get("gnews_country")  # ex: "FR" / "US"
    max_results = int(config.get("max_results", 10))

    google = GNews(
        language=lang if lang else None,
        country=country if country else None,
        max_results=max_results,
        period="1d",
    )

    try:
        raw = google.get_news_by_query(query)
    except Exception as e:
        print(f"Erreur GNews: {e}")
        return []

    if not raw:
        print("GNews n’a rien renvoyé.")
        return []

    print(f"{len(raw)} bruts depuis GNews.")
    cleaned = []
    for it in raw:
        url = (it.get("url") or "").strip()
        if not url or "example.com" in url or "URL_DE_TON_ARTICLE_SOURCE_POUR_LENQUETE" in url:
            continue

        title = (it.get("title") or "").strip()
        published_raw = it.get("published date") or it.get("published_date") or it.get("publishedAt") or it.get("date")
        published_iso = _to_iso(published_raw)

        body = _fetch_article_body(url)
        if not body:
            # fallback: description si assez longue
            desc = (it.get("description") or "").strip()
            if len(desc) >= 80:
                body = desc
            else:
                print(f"Contenu inexploitable, skip: {url}")
                continue

        cleaned.append({
            "url": url,
            "title": title,
            "publishedAt": published_iso,
            "content": body,
        })

    print(f"{len(cleaned)} article(s) exploitables après filtrage.")
    return cleaned

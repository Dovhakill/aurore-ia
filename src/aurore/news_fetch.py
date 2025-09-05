# -*- coding: utf-8 -*-
import os
import sys
import re
import requests
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from gnews import GNews
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

BAD_URL_PATTERNS = (
    "URL_DE_TON_ARTICLE_SOURCE_POUR_LENQUETE",
    "example.com",
)

def _is_valid_url(u: str) -> bool:
    if not u or any(x in u for x in BAD_URL_PATTERNS):
        return False
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

def _to_iso(dt_like: Optional[str]) -> str:
    """
    Normalise la date en ISO 8601 UTC.
    GNews peut renvoyer: 'Tue, 21 Jan 2025 18:00:00 GMT' ou None.
    """
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
    # Heuristique simple : paragraphes non vides et raisonnablement longs
    parts = []
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if t and len(t) >= 40:
            parts.append(t)
    text = "\n\n".join(parts)
    # garde < 8000 chars pour éviter d’exploser la limite modèle
    return text[:8000].strip()

def _fetch_article_body(url: str) -> Optional[str]:
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        text = _extract_text(r.text)
        if len(text) < 80:
            # Contenu trop court -> inutile pour la synthèse
            return None
        return text
    except Exception as e:
        print(f"WARN fetch échoué {url}: {e}")
        return None

def get_news_from_api(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Retourne une liste d’articles exploitables:
    [
      {"url":..., "title":..., "publishedAt": ISO8601, "content": ...},
      ...
    ]
    Utilise la config:
      - gnews_topic (optionnel)
      - gnews_lang (ex: 'fr', 'en')  [defaut 'en']
      - gnews_country (ex: 'FR','US') [defaut 'US']
      - search_query (optionnel)
      - max_results (optionnel, defaut 10)
    """
    lang = config.get("gnews_lang", "en")
    country = config.get("gnews_country", "US")
    max_results = int(config.get("max_results", 10))
    topic = config.get("gnews_topic")
    query = config.get("search_query")

    google = GNews(language=lang, country=country, max_results=max_results, period="1d")

    try:
        if query:
            raw = google.get_news_by_query(query)
        elif topic:
            raw = google.get_top_news_by_topic(topic)
        else:
            raw = google.get_top_news()
    except Exception as e:
        print(f"Erreur GNews: {e}")
        return []

    if not raw:
        print("GNews n’a rien renvoyé.")
        return []

    print(f"{len(raw)} bruts depuis GNews.")

    cleaned: List[Dict[str, Any]] = []
    for it in raw:
        url = (it.get("url") or "").strip()
        title = (it.get("title") or "").strip()

        if not _is_valid_url(url):
            print(f"Skip URL invalide: {url or '<vide>'}")
            continue

        body = _fetch_article_body(url)
        if not body:
            # Fallback: description si présente
            fallback = (it.get("description") or "").strip()
            if len(fallback) >= 80:
                body = fallback
            else:
                print(f"Contenu inexploitable, skip: {url}")
                continue

        # Normalisation date
        published_raw = (
            it.get("published date")
            or it.get("published_date")
            or it.get("publishedAt")
            or it.get("date")
        )
        published_iso = _to_iso(published_raw)

        cleaned.append({
            "url": url,
            "title": title,
            "publishedAt": published_iso,
            "content": body,
        })

    print(f"{len(cleaned)} article(s) exploitables après filtrage.")
    return cleaned

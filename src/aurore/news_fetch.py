# -*- coding: utf-8 -*-
"""
news_fetch.py
- Compatible avec différentes versions de la lib 'gnews' (get_news_by_query / get_news / get_news_by_keyword).
- Fallback robuste via RSS Google News si la lib ne fournit pas la méthode attendue.
- Extraction de texte simple via BeautifulSoup.
"""

from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urlencode
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
import requests
import feedparser
from bs4 import BeautifulSoup

try:
    # La lib n'est pas obligatoire si le fallback RSS suffit
    from gnews import GNews
except Exception:
    GNews = None

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# --------------------------
# Utilitaires
# --------------------------
def _to_iso(dt_like: Optional[str]) -> str:
    if not dt_like:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = parsedate_to_datetime(str(dt_like))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        # Certains feeds donnent déjà de l’ISO 8601 → on tente direct
        try:
            s = str(dt_like).strip()
            if s.endswith("Z"):
                return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
            return datetime.fromisoformat(s).astimezone(timezone.utc).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Nettoyage des éléments non textuels
    for tag in soup(["script", "style", "noscript", "header", "footer", "aside", "form", "nav"]):
        tag.decompose()
    parts = []
    # On reste simple et robuste : paragraphes suffisamment longs
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if t and len(t) >= 40:
            parts.append(t)
    text = "\n\n".join(parts)
    return text[:8000].strip()

def _fetch_article_body(url: str) -> Optional[str]:
    try:
        if not url or not url.startswith(("http://", "https://")):
            return None
        r = requests.get(url, timeout=12, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        text = _extract_text(r.text)
        if len(text) < 80:
            return None
        return text
    except Exception as e:
        print(f"WARN fetch échoué {url}: {e}")
        return None

def _clean_url(url: str) -> Optional[str]:
    try:
        if not url:
            return None
        u = url.strip()
        if not u.startswith(("http://", "https://")):
            return None
        if "example.com" in u or "URL_DE_TON_ARTICLE_SOURCE_POUR_LENQUETE" in u:
            return None
        return u
    except Exception:
        return None

def _source_from_url(url: str) -> str:
    try:
        netloc = urlparse(url).netloc
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return "source"

# --------------------------
# GNews lib (multi-versions)
# --------------------------
def _via_gnews_library(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    if GNews is None:
        return []

    query = (config.get("gnews_query") or "").strip()
    if not query:
        print("gnews_query manquant dans config de la verticale.")
        return []

    lang = config.get("gnews_lang") or None
    country = config.get("gnews_country") or None
    max_results = int(config.get("max_results", 10))

    google = GNews(
        language=lang if lang else None,
        country=country if country else None,
        max_results=max_results,
        period="1d",
    )

    raw = None
    # Supporte plusieurs variantes de la lib
    if hasattr(google, "get_news_by_query"):
        raw = google.get_news_by_query(query)
    elif hasattr(google, "get_news"):
        raw = google.get_news(query)
    elif hasattr(google, "get_news_by_keyword"):
        raw = google.get_news_by_keyword(query)
    else:
        print("Version de gnews non supportée (aucune méthode de requête).")

    if not raw:
        return []

    print(f"{len(raw)} bruts depuis gnews (lib).")
    cleaned: List[Dict[str, Any]] = []
    for it in raw:
        # La structure peut varier selon la version → on essaie plusieurs clés
        url = _clean_url(it.get("url") or it.get("link") or "")
        if not url:
            continue

        title = (it.get("title") or "").strip()
        published_raw = (
            it.get("published date")
            or it.get("published_date")
            or it.get("publishedAt")
            or it.get("date")
            or it.get("published")
        )
        published_iso = _to_iso(published_raw)

        body = _fetch_article_body(url)
        if not body:
            desc = (it.get("description") or "").strip()
            if len(desc) >= 80:
                body = desc
            else:
                print(f"Contenu inexploitable (lib), skip: {url}")
                continue

        cleaned.append({
            "url": url,
            "title": title,
            "publishedAt": published_iso,
            "content": body,
            "source": _source_from_url(url),
        })

    return cleaned

# --------------------------
# Fallback RSS Google News
# --------------------------
def _build_rss_url(query: str, lang: Optional[str], country: Optional[str]) -> str:
    base = "https://news.google.com/rss/search"
    params = {"q": query}
    # Localisation si fournie dans la conf
    if lang and country:
        params["hl"] = lang
        params["gl"] = country
        params["ceid"] = f"{country}:{lang}"
    return f"{base}?{urlencode(params)}"

def _via_google_rss(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    query = (config.get("gnews_query") or "").strip()
    if not query:
        return []

    lang = config.get("gnews_lang") or None
    country = config.get("gnews_country") or None
    url = _build_rss_url(query, lang, country)
    feed = feedparser.parse(url)

    if not feed or not feed.entries:
        print("RSS Google News vide.")
        return []

    print(f"{len(feed.entries)} bruts depuis RSS Google News.")
    cleaned: List[Dict[str, Any]] = []
    for e in feed.entries[: int(config.get("max_results", 10))]:
        url = _clean_url(getattr(e, "link", "") or "")
        if not url:
            continue

        title = (getattr(e, "title", "") or "").strip()
        published = getattr(e, "published", None) or getattr(e, "updated", None)
        published_iso = _to_iso(published)
        body = _fetch_article_body(url)
        if not body:
            summary = (getattr(e, "summary", "") or "").strip()
            if len(summary) >= 80:
                body = summary
            else:
                print(f"Contenu inexploitable (RSS), skip: {url}")
                continue

        cleaned.append({
            "url": url,
            "title": title,
            "publishedAt": published_iso,
            "content": body,
            "source": _source_from_url(url),
        })

    return cleaned

# --------------------------
# Entrée principale
# --------------------------
def get_news_from_api(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Essaie d'abord la lib 'gnews' (peu importe la version),
    puis bascule sur le flux RSS Google News si besoin.
    """
    # 1) Lib gnews (multi-versions)
    try:
        data = _via_gnews_library(config)
        if data:
            return data
    except Exception as e:
        print(f"Erreur gnews (lib): {e}")

    # 2) Fallback RSS
    try:
        data = _via_google_rss(config)
        if data:
            return data
    except Exception as e:
        print(f"Erreur RSS: {e}")

    print("GNews n’a rien renvoyé (lib + RSS).")
    return []

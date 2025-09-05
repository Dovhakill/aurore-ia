# -*- coding: utf-8 -*-
"""
news_fetch.py
- Récupère des articles via RSS Google News (search OU topic)
- Résout les liens Google News vers l'URL finale
- Extrait un texte lisible depuis la page (HTML -> texte)
"""
from __future__ import annotations

import time
import html
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode, quote, urlparse, parse_qs

import requests
import feedparser
from bs4 import BeautifulSoup


UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)


def _iso(dt_struct) -> str:
    if not dt_struct:
        return datetime.now(timezone.utc).isoformat()
    try:
        return datetime.fromtimestamp(time.mktime(dt_struct), tz=timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _final_url(url: str, timeout: float = 10.0) -> str:
    """
    Résout les redirections Google News vers la source d'origine.
    - Si le lien contient ?url=, on renvoie ce param.
    - Sinon on suit les redirections HTTP.
    """
    if not url:
        return url

    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query or "")
        if "url" in qs and qs["url"]:
            return qs["url"][0]
    except Exception:
        pass

    try:
        with requests.get(url, headers={"User-Agent": UA}, timeout=timeout, allow_redirects=True) as r:
            r.raise_for_status()
            return r.url
    except Exception:
        return url


def _extract_text_from_html(html_str: str) -> str:
    """Extraction simple : priorité aux <article>, sinon concat <p>."""
    soup = BeautifulSoup(html_str, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "picture", "source"]):
        tag.decompose()

    # zone article prioritaire
    main = soup.find("article")
    if not main:
        # fallback : gros container de contenu possible
        main = soup.find("main") or soup.find("div", attrs={"role": "main"}) or soup

    # récup paragraphes
    paras = []
    for p in main.find_all("p"):
        txt = p.get_text(" ", strip=True)
        if txt and len(txt) > 30:
            paras.append(txt)

    text = "\n\n".join(paras).strip()

    # mini nettoyage
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _fetch_article_body(url: str, timeout: float = 12.0) -> str:
    try:
        with requests.get(url, headers={"User-Agent": UA}, timeout=timeout) as r:
            r.raise_for_status()
            return _extract_text_from_html(r.text)
    except Exception:
        return ""


def _domain(u: str) -> str:
    try:
        return urlparse(u).netloc or ""
    except Exception:
        return ""


def _build_rss_url_from_query(query: str, lang: str, country: str) -> str:
    # query arrive depuis config.json : les guillemets sont déjà échappés pour le JSON.
    q = query
    hl = f"{lang}-{country}"
    qs = {
        "q": q,
        "hl": hl,
        "gl": country,
        "ceid": f"{country}:{lang}",
    }
    return "https://news.google.com/rss/search?" + urlencode(qs, safe=" :()\"")


def _build_rss_url_from_topic(topic: str, lang: str, country: str) -> str:
    hl = f"{lang}-{country}"
    return (
        f"https://news.google.com/rss/headlines/section/topic/{quote(topic)}"
        f"?hl={hl}&gl={country}&ceid={country}:{lang}"
    )


def get_news_from_api(vcfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Retourne une liste d'articles normalisés:
    [
      {
        "url": "...",               # URL finale
        "title": "...",
        "content": "...",           # texte long extrait
        "publishedAt": "ISO8601",
        "source": "domaine"
      },
      ...
    ]
    """
    lang = (vcfg.get("gnews_lang") or "fr").lower()
    country = (vcfg.get("gnews_country") or "FR").upper()
    max_results = int(vcfg.get("max_results") or 8)

    rss_url: Optional[str] = None
    if vcfg.get("gnews_query"):
        rss_url = _build_rss_url_from_query(vcfg["gnews_query"], lang, country)
    elif vcfg.get("gnews_topic"):
        rss_url = _build_rss_url_from_topic(vcfg["gnews_topic"], lang, country)

    items: List[Dict[str, Any]] = []

    if not rss_url:
        # Rien de configuré
        return items

    parsed = feedparser.parse(rss_url)
    entries = parsed.get("entries") or []
    if not entries:
        return items

    for e in entries[:max_results]:
        link = (e.get("link") or "").strip()
        title = html.unescape((e.get("title") or "").strip())
        published = _iso(e.get("published_parsed"))

        if not link or not title:
            continue

        fin = _final_url(link)
        text = _fetch_article_body(fin)
        src = _domain(fin)

        items.append(
            {
                "url": fin,
                "title": title,
                "content": text or (html.unescape((e.get("summary") or "").strip())),
                "publishedAt": published,
                "source": src,
            }
        )

    return items

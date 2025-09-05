# -*- coding: utf-8 -*-
import os, json, hashlib, requests
from typing import Set, Dict, Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

BLOB_KEY   = "processed_urls"
KEY_PREFIX = "processed:"

def _normalize_url(u: str) -> str:
    try:
        p = urlparse(u)
        netloc = p.netloc.replace("www.", "")
        q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
        return urlunparse((p.scheme, netloc, p.path, "", urlencode(q), ""))
    except Exception:
        return u

def _key_for(u: str) -> str:
    n = _normalize_url(u)
    h = hashlib.sha256(n.encode("utf-8")).hexdigest()
    return KEY_PREFIX + h

def _store_name(config: dict) -> str:
    return config.get("blob_store_name", "aurore-memory")

def _site_id() -> str:
    return os.environ["NETLIFY_SITE_ID"]

def _token_direct() -> str:
    return os.environ["NETLIFY_BLOBS_TOKEN"]

def _base_direct(config: dict) -> str:
    return f"https://api.netlify.com/api/v1/sites/{_site_id()}/blobs/{_store_name(config)}"

def _headers_direct() -> dict:
    return {"Authorization": f"Bearer {_token_direct()}", "Content-Type": "application/json", "User-Agent": "Aurore/1.0"}

def get_processed_urls(config: dict) -> Set[str]:
    try:
        url = _base_direct(config) + f"/{BLOB_KEY}"
        r = requests.get(url, headers=_headers_direct(), timeout=10)
        if r.status_code == 200:
            arr = r.json() or []
            urls = set(_normalize_url(u) for u in arr if isinstance(u, str))
            print(f"Legacy mémoire: {len(urls)} URLs")
            return urls
        return set()
    except Exception as e:
        print(f"WARN lecture legacy: {e}")
        return set()

def save_processed_urls(urls_set: Set[str], config: dict) -> None:
    try:
        payload = [_normalize_url(u) for u in urls_set]
        url = _base_direct(config) + f"/{BLOB_KEY}"
        r = requests.put(url, headers=_headers_direct(), json=payload, timeout=10)
        r.raise_for_status()
        print(f"Legacy sauvegardée: {len(payload)} URLs")
    except Exception as e:
        print(f"WARN sauvegarde legacy: {e}")

def has_processed(url: str, config: dict) -> bool:
    try:
        k = _key_for(url)
        u = _base_direct(config) + f"/{k}"
        r = requests.get(u, headers=_headers_direct(), timeout=10)
        return r.status_code == 200 and bool(r.text)
    except Exception:
        return False

def mark_processed(url: str, published_iso: Optional[str], config: dict) -> None:
    try:
        k = _key_for(url)
        meta = {"processedAt": published_iso or None}
        u = _base_direct(config) + f"/{k}"
        r = requests.put(u, headers=_headers_direct(), json=meta, timeout=10)
        if r.status_code not in (200, 201):
            print(f"WARN setJSON {r.status_code} – {r.text}")
    except Exception as e:
        print(f"WARN mark_processed: {e}")

def find_first_unique_article(articles: list, processed_urls: Set[str]) -> Optional[Dict]:
    print(f"Recherche d'un article unique parmi {len(articles)} candidats…")
    for article in articles:
        url = (article.get('url') or "").strip()
        if not url:
            continue
        n = _normalize_url(url)
        if n not in processed_urls and not has_processed(n, {}):
            print(f"Article unique trouvé : {article.get('title', '')}")
            return article
    print("Aucun article unique trouvé.")
    return None

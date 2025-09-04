# -*- coding: utf-8 -*-
import os, json, hashlib, requests
from typing import Set, Dict, Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# ----- Constantes -----
BLOB_KEY   = "processed_urls"       # Legacy list (compat pour migration douce)
KEY_PREFIX = "processed:"           # Nouvelles clés par article

# ----- Utils URL -----
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

# ----- Mode détection -----
def _has_proxy() -> bool:
    return bool(os.environ.get("BLOBS_PROXY_URL"))

def _token_proxy() -> str:
    # On accepte AURORE_BLOBS_TOKEN (recommandé) ou NETLIFY_BLOBS_TOKEN
    return os.environ.get("AURORE_BLOBS_TOKEN") or os.environ.get("NETLIFY_BLOBS_TOKEN") or ""

def _headers_proxy() -> dict:
    return {"X-AURORE-TOKEN": _token_proxy(), "Content-Type": "application/json", "User-Agent": "Aurore/1.0"}

def _url_proxy() -> str:
    return os.environ["BLOBS_PROXY_URL"].rstrip("/")

# ----- Direct Netlify API -----
def _site_id() -> str:
    return os.environ["NETLIFY_SITE_ID"]

def _token_direct() -> str:
    return os.environ["NETLIFY_BLOBS_TOKEN"]

def _store_name(config: dict) -> str:
    return config.get("blob_store_name", "aurore-memory")

def _base_direct(config: dict) -> str:
    return f"https://api.netlify.com/api/v1/sites/{_site_id()}/blobs/{_store_name(config)}"

def _headers_direct() -> dict:
    return {"Authorization": f"Bearer {_token_direct()}", "Content-Type": "application/json", "User-Agent": "Aurore/1.0"}

# ----- Legacy list (pour migration douce) -----
def get_processed_urls(config: dict) -> Set[str]:
    """Lit la liste legacy des URLs (BLOB_KEY). Retourne un set normalisé."""
    try:
        if _has_proxy():
            r = requests.get(_url_proxy() + f"?key={BLOB_KEY}", headers=_headers_proxy(), timeout=10)
            if r.status_code == 200:
                arr = r.json() or []
                urls = set(_normalize_url(u) for u in arr if isinstance(u, str))
                print(f">>> Mémoire legacy (proxy): {len(urls)} URLs")
                return urls
            print(f">>> Pas de mémoire legacy (proxy code {r.status_code})")
            return set()
        else:
            url = _base_direct(config) + f"/{BLOB_KEY}"
            r = requests.get(url, headers=_headers_direct(), timeout=10)
            if r.status_code == 200:
                arr = r.json() or []
                urls = set(_normalize_url(u) for u in arr if isinstance(u, str))
                print(f">>> Mémoire legacy (direct): {len(urls)} URLs")
                return urls
            print(f">>> Pas de mémoire legacy (direct code {r.status_code})")
            return set()
    except Exception as e:
        print(f">>> Lecture mémoire legacy impossible: {e}")
        return set()

def save_processed_urls(urls_set: Set[str], config: dict) -> None:
    """Écrit la liste legacy (compat)."""
    try:
        payload = [_normalize_url(u) for u in urls_set]
        if _has_proxy():
            r = requests.post(_url_proxy(), headers=_headers_proxy(), data=json.dumps({"key": BLOB_KEY, "meta": payload}), timeout=10)
            r.raise_for_status()
            print(f">>> SUCCÈS: {len(payload)} URLs sauvegardées (legacy via proxy).")
        else:
            url = _base_direct(config) + f"/{BLOB_KEY}"
            r = requests.put(url, headers=_headers_direct(), json=payload, timeout=10)
            r.raise_for_status()
            print(f">>> SUCCÈS: {len(payload)} URLs sauvegardées (legacy direct).")
    except requests.exceptions.RequestException as e:
        print(">>> Échec de la sauvegarde legacy.")
        if getattr(e, "response", None) is not None:
            print(f"Status: {e.response.status_code} Body: {e.response.text}")
        else:
            print(f"Erreur: {e}")
    finally:
        print("--- Fin sauvegarde legacy ---")

# ----- Nouvelles clés par article -----
def has_processed(url: str, config: dict) -> bool:
    try:
        k = _key_for(url)
        if _has_proxy():
            r = requests.get(_url_proxy() + f"?key={k}", headers=_headers_proxy(), timeout=10)
            return r.status_code == 200 and bool(r.text)
        else:
            u = _base_direct(config) + f"/{k}"
            r = requests.get(u, headers=_headers_direct(), timeout=10)
            return r.status_code == 200 and bool(r.text)
    except Exception as e:
        print(f">>> Erreur has_processed: {e}")
        return False

def mark_processed(url: str, published_iso: Optional[str], config: dict) -> None:
    try:
        k = _key_for(url)
        meta = {"processedAt": published_iso or None}
        if _has_proxy():
            r = requests.post(_url_proxy(), headers=_headers_proxy(), data=json.dumps({"key": k, "meta": meta}), timeout=10)
            if r.status_code not in (200, 201):
                print(f">>> WARN proxy setJSON {r.status_code} – {r.text}")
        else:
            u = _base_direct(config) + f"/{k}"
            r = requests.put(u, headers=_headers_direct(), json=meta, timeout=10)
            if r.status_code not in (200, 201):
                print(f">>> WARN direct setJSON {r.status_code} – {r.text}")
    except Exception as e:
        print(f">>> Erreur mark_processed: {e}")

# ----- Sélection article -----
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

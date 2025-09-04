<<<<<<< HEAD
import os, json, hashlib, requests
=======
import os
import sys
import json
import requests
>>>>>>> f1093225e097ed469ec0914a19a758b8892df8cd
from typing import Set, Dict, Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

<<<<<<< HEAD
# Legacy list key (kept for migration)
=======
>>>>>>> f1093225e097ed469ec0914a19a758b8892df8cd
BLOB_KEY = "processed_urls"
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

def _proxy_headers():
    return {
        "X-AURORE-TOKEN": os.environ["AURORE_BLOBS_TOKEN"],
        "Content-Type": "application/json",
        "User-Agent": "Aurore/1.0",
    }

def _proxy_url(config: dict) -> str:
    return os.environ["BLOBS_PROXY_URL"].rstrip("/")

def find_first_unique_article(articles: list, processed_urls: Set[str]) -> Optional[Dict]:
<<<<<<< HEAD
    """
    Parcourt la liste des articles et retourne le premier dont l'URL normalisée n'est pas
    dans le set des URLs déjà traitées (legacy) ET pas marqué via les clés par article.
    """
    print(f"Recherche d'un article unique parmi {len(articles)} articles trouvés...")
    for article in articles:
        url = article.get('url')
        if not url:
            continue
        n = _normalize_url(url)
        if n not in processed_urls and not has_processed(n, {}):
            print(f"Article unique trouvé : {article.get('title', '')}")
            return article
    print("Aucun article unique trouvé.")
    return None

def get_processed_urls(config: dict) -> Set[str]:
    """
    MIGRATION DOUCE : lit la liste legacy (BLOB_KEY) via proxy si présente.
    """
    try:
        r = requests.get(_proxy_url(config) + f"?key={BLOB_KEY}", headers=_proxy_headers(), timeout=10)
        if r.status_code == 200:
            arr = r.json() or []
            urls = set(_normalize_url(u) for u in arr if isinstance(u, str))
            print(f">>> Mémoire legacy: {len(urls)} URLs")
            return urls
        print(f">>> Pas de mémoire legacy (code {r.status_code})")
        return set()
    except Exception as e:
        print(f">>> Lecture mémoire legacy impossible: {e}")
        return set()

def has_processed(url: str, config: dict) -> bool:
    try:
        k = _key_for(url)
        r = requests.get(_proxy_url(config) + f"?key={k}", headers=_proxy_headers(), timeout=10)
        if r.status_code == 200 and r.text:
            return True
        return False
    except Exception as e:
        print(f">>> Erreur has_processed: {e}")
        return False

def mark_processed(url: str, published_iso: Optional[str], config: dict) -> None:
    try:
        k = _key_for(url)
        payload = {"key": k, "meta": {"processedAt": published_iso or None}}
        r = requests.post(_proxy_url(config), headers=_proxy_headers(), data=json.dumps(payload), timeout=10)
        if r.status_code not in (200, 201):
            print(f">>> WARN: proxy setJSON {r.status_code} – {r.text}")
    except Exception as e:
        print(f">>> Erreur mark_processed: {e}")

def save_processed_urls(urls_set: Set[str], config: dict) -> None:
    """
    **Legacy**: sauvegarde la liste d'URLs traitées (pour compatibilité).
    """
    try:
        data_payload = [u for u in urls_set]
        r = requests.post(_proxy_url(config), headers=_proxy_headers(),
                          data=json.dumps({"key": BLOB_KEY, "meta": data_payload}), timeout=10)
        r.raise_for_status()
        print(f">>> SUCCÈS: {len(data_payload)} URLs sauvegardées (legacy).")
    except requests.exceptions.RequestException as e:
        print(">>> ERREUR CRITIQUE: Échec de la sauvegarde (legacy).")
        if getattr(e, "response", None) is not None:
            print(f"Status Code: {e.response.status_code}")
            print(f"Réponse de l'API: {e.response.text}")
        else:
            print(f"Erreur de connexion: {e}")
    finally:
        print("--- Fin de la sauvegarde dans Netlify Blobs (legacy) ---")
=======
    for article in articles:
        if article['url'] not in processed_urls:
            return article
    return None

def get_processed_urls(config: dict) -> Set[str]:
    blob_store_url = f"https://api.netlify.com/api/v1/sites/{os.environ['NETLIFY_SITE_ID']}/blobs/{config.get('blob_store_name')}"
    headers = {"Authorization": f"Bearer {os.environ['NETLIFY_BLOBS_TOKEN']}"}
    try:
        response = requests.get(f"{blob_store_url}/{BLOB_KEY}", headers=headers)
        if response.status_code == 404:
            return set()
        response.raise_for_status()
        return set(response.json())
    except Exception as e:
        print(f"ERREUR LECTURE NETLIFY BLOBS: {e}")
        return set()

def save_processed_urls(urls_to_save: Set[str], config: dict):
    blob_store_url = f"https://api.netlify.com/api/v1/sites/{os.environ['NETLIFY_SITE_ID']}/blobs/{config.get('blob_store_name')}"
    headers = {"Authorization": f"Bearer {os.environ['NETLIFY_BLOBS_TOKEN']}"}
    try:
        response = requests.put(f"{blob_store_url}/{BLOB_KEY}", headers=headers, json=list(urls_to_save))
        response.raise_for_status() 
        print(f">>> SUCCÈS: {len(urls_to_save)} URLs sauvegardées.")
    except Exception as e:
        print(f"ERREUR SAUVEGARDE NETLIFY BLOBS: {e}")
>>>>>>> f1093225e097ed469ec0914a19a758b8892df8cd

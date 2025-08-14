# src/aurore/news_fetch.py
import requests
import json
from urllib.parse import urlparse
from .config import Settings

# On construit l'URL du nouveau proxy GNews à partir de l'URL du proxy mémoire
GNEWS_PROXY_URL = Settings.BLOBS_PROXY_URL.replace("blobs-proxy", "gnews-proxy")

def _auth_headers():
    """Prépare les en-têtes pour s'authentifier auprès de nos PROPRES proxys."""
    return {"X-AURORE-TOKEN": Settings.AURORE_BLOBS_TOKEN}

def fetch_top_fr(page_size: int = 40):
    """Récupère les news en appelant notre propre proxy Netlify."""
    
    r = requests.get(GNEWS_PROXY_URL, headers=_auth_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    
    out = []
    for a in data.get("articles", []):
        if not a.get("url") or not a.get("title"):
            continue
        
        out.append({
            "title": a.get("title", "").strip(),
            "url": a.get("url"),
            "source": a.get("source", {}).get("name", ""),
            "publishedAt": a.get("publishedAt", ""),
            "description": a.get("description", "") or "",
        })
    return out

# Note : cette fonction n'est plus très fiable car on ne peut pas faire de recherche
# aussi précise via notre proxy simple. On la garde simplifiée.
def find_additional_sources(topic: str, existing_url: str, max_sources: int = 3):
    return [existing_url]

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return ""

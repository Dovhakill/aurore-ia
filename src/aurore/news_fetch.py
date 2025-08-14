# src/aurore/news_fetch.py
import requests
from urllib.parse import urlparse
from .config import Settings

# Nouvelle URL de l'API GNews
GNEWS_API_TOP = "https://gnews.io/api/v4/top-headlines"
GNEWS_API_SEARCH = "https://gnews.io/api/v4/search"

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return ""

def fetch_top_fr(page_size: int = 40):
    """Fetches general international top headlines from GNews."""
    params = {
        "apikey": Settings.GNEWS_API_KEY,
        "lang": "fr",
        "max": page_size,
    }
    
    r = requests.get(GNEWS_API_TOP, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    
    out = []
    # La structure de la réponse de GNews est légèrement différente
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

def find_additional_sources(topic: str, existing_url: str, max_sources: int = 3):
    """Finds additional sources for a given topic using GNews."""
    params = {
        "apikey": Settings.GNEWS_API_KEY,
        "q": f'"{topic}"',
        "lang": "fr",
        "max": 15,
    }
    try:
        r = requests.get(GNEWS_API_SEARCH, params=params, timeout=20)
        r.raise_for_status()
        articles = r.json().get("articles", [])
    except Exception:
        articles = []

    sources = [existing_url]
    domains_seen = {_domain(existing_url)}
    
    for art in articles:
        url = art.get("url")
        if not url:
            continue
            
        dom = _domain(url)
        if dom and dom not in domains_seen:
            domains_seen.add(dom)
            sources.append(url)
            if len(sources) >= max_sources:
                break
                
    return sources

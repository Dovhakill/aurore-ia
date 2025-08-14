import requests
from urllib.parse import urlparse
from .config import Settings

# On utilise l'endpoint /top-headlines pour les actualités générales
NEWSAPI_TOP = "https://newsapi.org/v2/top-headlines"
NEWSAPI_EVERYTHING = "https://newsapi.org/v2/everything"

def _domain(url: str) -> str:
    """Helper function to extract the domain from a URL."""
    try:
        return urlparse(url).netloc
    except Exception:
        return ""

def fetch_top_fr(page_size: int = 40):
    """
    Fetches general international top headlines from French-speaking sources.
    """
    params = {
        "apiKey": Settings.NEWSAPI_KEY,
        "language": "fr",  # On garde le filtre de la langue
        "pageSize": page_size,
        # On enlève "country" et "q" pour avoir les news internationales
    }
    
    r = requests.get(NEWSAPI_TOP, params=params, timeout=20)
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

def find_additional_sources(topic: str, existing_url: str, max_sources: int = 3):
    """Finds additional sources for a given topic."""
    params = {
        "apiKey": Settings.NEWSAPI_KEY,
        "q": f'"{topic}"',
        "language": "fr",
        "sortBy": "relevancy",
        "pageSize": 15
    }
    try:
        r = requests.get(NEWSAPI_EVERYTHING, params=params, timeout=20)
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

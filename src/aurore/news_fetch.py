import requests
from urllib.parse import urlparse
from .config import Settings

NEWSAPI_TOP = "https://newsapi.org/v2/top-headlines"
NEWSAPI_EVERYTHING = "https://newsapi.org/v2/everything"

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return ""

def fetch_top_fr(page_size: int = 20, category: str | None = None):
    params = {
        "apiKey": Settings.NEWSAPI_KEY,
        "language": "fr",
        "pageSize": page_size,
        "country": "fr"
    }
    if category:
        params["category"] = category
    r = requests.get(NEWSAPI_TOP, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    out = []
    for a in data.get("articles", []):
        if not a.get("url"):
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
    params = {
        "apiKey": Settings.NEWSAPI_KEY,
        "q": topic,
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
        if dom in domains_seen:
            continue
        domains_seen.add(dom)
        sources.append(url)
        if len(sources) >= max_sources:
            break
    return sources
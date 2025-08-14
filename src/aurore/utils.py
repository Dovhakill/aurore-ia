import hashlib
import re
from urllib.parse import urlparse

def canonical_slug(title: str) -> str:
    t = re.sub(r"[^a-z0-9]+", "-", title.lower())
    return re.sub(r"-+", "-", t).strip("-")[:80]

def topic_key(title: str, urls: list) -> str:
    base = title.strip().lower() + "|" + "|".join(sorted(urls))
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

def domain(u: str) -> str:
    try:
        return urlparse(u).netloc
    except Exception:
        return ""
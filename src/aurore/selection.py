# -*- coding: utf-8 -*-
"""
selection.py
- Normalisation d'URL + hash
- Choix de l'article le plus récent non traité
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Set
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode


IGNORED_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}


def normalize_url(u: str) -> str:
    try:
        p = urlparse(u)
        scheme = p.scheme.lower()
        netloc = p.netloc.lower()

        # tri des query params + suppression tracking
        q = [(k, v) for (k, v) in parse_qsl(p.query, keep_blank_values=True) if k not in IGNORED_PARAMS]
        q.sort()
        query = urlencode(q, doseq=True)

        # sans fragment
        fragless = (scheme, netloc, p.path, p.params, query, "")

        return urlunparse(fragless)
    except Exception:
        return u


def hash_url(u: str) -> str:
    n = normalize_url(u)
    return hashlib.sha256(n.encode("utf-8")).hexdigest()


def _parse_iso(dt: str) -> float:
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def pick_freshest_unique(
    articles: list[Dict[str, Any]], seen_hashes: Set[str], min_chars: int = 600
) -> Optional[Tuple[Dict[str, Any], str]]:
    """
    Tri par date décroissante, prend le premier:
    - pas encore vu (hash URL)
    - contenu suffisant
    """
    if not articles:
        return None

    # tri par date
    arts = sorted(articles, key=lambda a: _parse_iso(a.get("publishedAt", "")), reverse=True)

    for a in arts:
        u = a.get("url") or ""
        h = hash_url(u)
        content = (a.get("content") or "").strip()
        if not u or h in seen_hashes or len(content) < min_chars:
            continue
        return a, h

    return None

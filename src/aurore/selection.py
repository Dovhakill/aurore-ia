# -*- coding: utf-8 -*-
"""
selection.py
- Normalisation d'URL + hash
- Choix de l'article le plus récent non traité avec seuil de longueur souple
"""
from __future__ import annotations

import os
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
    articles: list[Dict[str, Any]],
    seen_hashes: Set[str],
    min_chars: Optional[int] = None,
) -> Optional[Tuple[Dict[str, Any], str]]:
    """
    Tri par date décroissante, retourne le premier article:
    - pas encore vu (hash URL)
    - contenu suffisant selon seuil souple
    Le seuil peut être forcé via la variable d'env MIN_CHARS.
    """
    # seuil dynamique
    if min_chars is None:
        try:
            min_chars = int(os.getenv("MIN_CHARS", "280"))
        except Exception:
            min_chars = 280

    if not articles:
        return None

    # tri par date (récent d'abord)
    arts = sorted(articles, key=lambda a: _parse_iso(a.get("publishedAt", "")), reverse=True)

    for a in arts:
        u = (a.get("url") or "").strip()
        if not u:
            continue
        h = hash_url(u)
        if h in seen_hashes:
            continue

        content = (a.get("content") or "").strip()
        if not content:
            continue

        # compactage léger
        content_compact = " ".join(content.split())
        length = len(content_compact)

        # règle principale
        if length >= min_chars:
            return a, h

        # règles bonus: texte pertinent même s'il est court
        words = content_compact.split()
        paras = [p for p in content.split("\n") if p.strip()]
        if len(words) >= 120 or len(paras) >= 3:
            return a, h

    return None

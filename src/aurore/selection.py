# -*- coding: utf-8 -*-
"""
selection.py
Stratégie de sélection pragmatique :
- Normalise les URLs (sans utm_* / www / trailing slash).
- Déduplique via set de hash SHA256 des URLs normalisées.
- Filtre les contenus trop courts.
- Choisit le plus récent (publishedAt) parmi les candidats restants.
"""

from typing import Dict, Any, Iterable, Optional, Tuple
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from datetime import datetime, timezone
import hashlib

_MIN_BODY_LEN = 120  # on évite les coquilles vides

def _strip_utm(query: str) -> str:
    if not query:
        return ""
    kept = [(k, v) for (k, v) in parse_qsl(query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlencode(kept, doseq=True)

def normalize_url(url: str) -> Optional[str]:
    """http(s) only, supprime www., utm_*, trailing slash."""
    if not url or not isinstance(url, str):
        return None
    u = url.strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        return None
    try:
        p = urlparse(u)
        if p.scheme not in ("http", "https"):
            return None
        netloc = p.netloc[4:] if p.netloc.startswith("www.") else p.netloc
        path = p.path.rstrip("/") or "/"
        query = _strip_utm(p.query)
        norm = urlunparse((p.scheme, netloc, path, "", query, ""))
        return norm
    except Exception:
        return None

def hash_url(norm_url: str) -> str:
    return hashlib.sha256(norm_url.encode("utf-8")).hexdigest()

def _to_iso(dt_like: str) -> str:
    """Accepte ISO divers ou RFC2822; renvoie ISO en UTC."""
    if not dt_like:
        return datetime.now(timezone.utc).isoformat()
    s = str(dt_like).strip()
    try:
        # ISO 8601 – avec ou sans Z
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        return datetime.fromisoformat(s).astimezone(timezone.utc).isoformat()
    except Exception:
        # RFC2822 etc.
        from email.utils import parsedate_to_datetime
        try:
            dt = parsedate_to_datetime(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

def _iso_to_dt(iso_s: str) -> datetime:
    try:
        return datetime.fromisoformat(iso_s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def pick_freshest_unique(
    candidates: Iterable[Dict[str, Any]],
    processed_hashes: Iterable[str],
    min_body_len: int = _MIN_BODY_LEN,
) -> Optional[Tuple[Dict[str, Any], str]]:
    """
    Retourne (article, article_hash) ou None.
    - Exclut les URLs déjà vues (via processed_hashes, SHA256 sur URL normalisée).
    - Exclut contenus trop courts.
    - Trie par date décroissante (publishedAt) et prend le 1er.
    """
    processed = set(processed_hashes or [])
    pool = []

    for it in (candidates or []):
        url = normalize_url(it.get("url") or it.get("link") or "")
        if not url:
            continue

        h = hash_url(url)
        if h in processed:
            # déja traité → on skip
            continue

        content = (it.get("content") or "").strip()
        if len(content) < min_body_len:
            # pas assez de matière pour la synthèse
            continue

        published_iso = _to_iso(it.get("publishedAt") or it.get("published") or it.get("date") or "")
        pool.append((it, h, published_iso))

    if not pool:
        return None

    # tri décroissant par date
    pool.sort(key=lambda row: _iso_to_dt(row[2]), reverse=True)
    best_item, best_hash, _ = pool[0]
    # on fixe l'URL normalisée et la date ISO au passage (défensif)
    best_item["url"] = normalize_url(best_item.get("url") or best_item.get("link") or best_item["url"])
    best_item["publishedAt"] = _to_iso(best_item.get("publishedAt") or best_item.get("published") or best_item.get("date") or "")
    return best_item, best_hash

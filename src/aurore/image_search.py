# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from typing import Optional

UA = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

def _get_meta(soup: BeautifulSoup, attr_name: str, attr_value: str) -> Optional[str]:
    try:
        tag = soup.find("meta", attrs={attr_name: attr_value})
        if tag and tag.get("content"):
            val = tag.get("content").strip()
            return val or None
    except Exception:
        pass
    return None

def find_image_from_source(url: str) -> Optional[str]:
    """
    Retourne l'URL d'une image représentative de la page source, ou None.
    - Priorité à <meta property="og:image"> puis <meta name="twitter:image">.
    - Ne lève jamais d'exception (log soft), pour ne jamais bloquer le pipeline.
    """
    if not url or not isinstance(url, str):
        return None

    try:
        resp = requests.get(url, timeout=10, headers=UA)
        resp.raise_for_status()
    except Exception as e:
        print(f"WARN image_search: fetch échoué {url}: {e}")
        return None

    try:
        soup = BeautifulSoup(resp.text, "html.parser")

        # 1) og:image
        img = _get_meta(soup, "property", "og:image")
        if img:
            return img

        # 2) twitter:image
        img = _get_meta(soup, "name", "twitter:image")
        if img:
            return img

        # 3) Parfois twitter:image:src
        img = _get_meta(soup, "name", "twitter:image:src")
        if img:
            return img

    except Exception as e:
        print(f"WARN image_search: parse échoué {url}: {e}")

    return None

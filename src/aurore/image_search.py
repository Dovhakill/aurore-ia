# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from typing import Optional

UA = {"User-Agent": "Mozilla/5.0"}

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
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=10, headers=UA)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for k in [("property", "og:image"), ("name", "twitter:image"), ("name", "twitter:image:src")]:
            img = _get_meta(soup, k[0], k[1])
            if img:
                return img
    except Exception as e:
        print(f"WARN image_search: {e}")
    return None

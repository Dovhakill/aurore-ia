import requests
from .config import Settings

def _auth_headers():
    return {"X-AURORE-TOKEN": Settings.AURORE_BLOBS_TOKEN}

def seen(key: str) -> bool:
    try:
        r = requests.get(f"{Settings.BLOBS_PROXY_URL}?key={key}", headers=_auth_headers(), timeout=15)
        if r.status_code == 404:
            return False
        r.raise_for_status()
        return True
    except requests.HTTPError:
        return True
    except Exception:
        return False

def mark(key: str, meta: dict):
    r = requests.post(Settings.BLOBS_PROXY_URL, headers=_auth_headers(), json={"key": key, "meta": meta}, timeout=20)
    r.raise_for_status()
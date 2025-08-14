import requests
from .config import Settings

def _auth_headers():
    return {"X-AURORE-TOKEN": Settings.AURORE_BLOBS_TOKEN}

def seen(key: str) -> bool:
    """Vérifie si une clé existe dans le Netlify Blob Store."""
    try:
        r = requests.get(
            f"{Settings.BLOBS_PROXY_URL}?key={key}",
            headers=_auth_headers(),
            timeout=15
        )
        if r.status_code == 404:
            return False  # Non vu
        r.raise_for_status()  # Lève une erreur pour les codes 401, 500, etc.
        return True  # Tout autre statut de succès signifie qu'il a été vu
    except requests.RequestException as e:
        print(f"ATTENTION : Impossible de contacter la mémoire : {e}. On considère comme non vu.")
        return False

def mark(key: str, meta: dict):
    """Marque une clé comme traitée dans la mémoire."""
    r = requests.post(
        Settings.BLOBS_PROXY_URL,
        headers=_auth_headers(),
        json={"key": key, "meta": meta},
        timeout=20
    )
    r.raise_for_status()

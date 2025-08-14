# src/aurore/dedup.py
import requests
from .config import Settings

def _auth_headers():
    return {"X-AURORE-TOKEN": Settings.AURORE_BLOBS_TOKEN}

def seen(key: str) -> bool:
    """Vérifie si une clé existe dans la mémoire (Netlify Blob Store)."""
    try:
        r = requests.get(f"{Settings.BLOBS_PROXY_URL}?key={key}", headers=_auth_headers(), timeout=15)

        # Cas 1: La clé n'existe pas, la mémoire le dit explicitement.
        if r.status_code == 404:
            return False

        # Cas 2: La clé existe.
        if r.status_code == 200:
            return True

        # Cas 3: Tout autre code d'erreur (401 Unauthorized, 500, etc.)
        # On lève une erreur pour que le log de GitHub Actions nous montre le problème.
        r.raise_for_status()
        return True # Ne sera atteint que pour les codes 2xx autres que 200

    except requests.RequestException as e:
        # En cas de problème réseau, on log l'erreur et on considère l'article comme "non vu".
        print(f"WARN: Impossible de contacter la mémoire : {e}. On continue sans déduplication pour cette clé.")
        return False

def mark(key: str, meta: dict):
    """Marque une clé comme traitée dans la mémoire."""
    r = requests.post(Settings.BLOBS_PROXY_URL, headers=_auth_headers(), json={"key": key, "meta": meta}, timeout=20)
    # Si le marquage échoue, on veut que le script s'arrête pour voir l'erreur.
    r.raise_for_status()

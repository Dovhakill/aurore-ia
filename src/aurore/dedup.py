import requests
from .config import Settings

def _auth_headers():
    """Prépare les en-têtes d'authentification pour la requête."""
    return {"X-AURORE-TOKEN": Settings.AURORE_BLOBS_TOKEN}

def seen(key: str) -> bool:
    """
    Vérifie si une clé d'article existe déjà dans la mémoire (Netlify Blob Store).
    Retourne True si l'article a été vu, False sinon.
    """
    try:
        r = requests.get(
            f"{Settings.BLOBS_PROXY_URL}?key={key}",
            headers=_auth_headers(),
            timeout=15
        )
        # Si la mémoire répond 404, la clé n'existe pas, donc l'article est nouveau.
        if r.status_code == 404:
            return False
        
        # Si la mémoire répond avec une autre erreur (token invalide, etc.), on lève l'erreur.
        r.raise_for_status()
        
        # Si la mémoire répond 200, la clé existe, donc l'article a déjà été vu.
        return True
        
    except requests.RequestException as e:
        # En cas de problème réseau, on affiche une alerte mais on considère l'article comme "nouveau" par sécurité.
        print(f"ATTENTION : Impossible de contacter la mémoire : {e}. On continue sans vérifier le doublon.")
        return False

def mark(key: str, meta: dict):
    """
    Marque une clé d'article comme "vue" en l'enregistrant dans la mémoire.
    """
    print(f"INFO : Marquage de la clé {key} comme traitée dans la mémoire.")
    r = requests.post(
        Settings.BLOBS_PROXY_URL,
        headers=_auth_headers(),
        json={"key": key, "meta": meta},
        timeout=20
    )
    # Si le marquage échoue, on veut que le script s'arrête pour voir l'erreur.
    r.raise_for_status()

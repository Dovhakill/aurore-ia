import requests
import time
from .config import Settings

def _auth_headers():
    """Prépare les en-têtes d'authentification."""
    return {"X-AURORE-TOKEN": Settings.AURORE_BLOBS_TOKEN}

def _make_request_with_retries(method, url, **kwargs):
    """Effectue une requête HTTP avec plusieurs tentatives en cas d'erreur serveur."""
    retries = 3
    delay = 2  # secondes
    for i in range(retries):
        try:
            if method.upper() == 'GET':
                r = requests.get(url, **kwargs)
            elif method.upper() == 'POST':
                r = requests.post(url, **kwargs)
            else:
                raise ValueError("Unsupported HTTP method")
            
            # Si la requête réussit (même avec une erreur client 4xx), on arrête les tentatives
            if r.status_code < 500:
                return r
            
            # Si c'est une erreur serveur 5xx, on affiche un message et on attend
            print(f"ATTENTION : Erreur serveur {r.status_code}. Tentative {i + 1}/{retries} dans {delay}s...")
            
        except requests.RequestException as e:
            print(f"ATTENTION : Erreur de connexion. Tentative {i + 1}/{retries} dans {delay}s... ({e})")
        
        # On attend avant la prochaine tentative
        time.sleep(delay)
        delay *= 2 # On augmente le délai à chaque fois (backoff exponentiel)

    # Si toutes les tentatives échouent, on lève la dernière erreur
    raise Exception(f"Échec de la communication avec la mémoire après {retries} tentatives.")


def seen(key: str) -> bool:
    """Vérifie si une clé existe dans la mémoire."""
    url = f"{Settings.BLOBS_PROXY_URL}?key={key}"
    r = _make_request_with_retries('GET', url, headers=_auth_headers(), timeout=15)
    
    if r.status_code == 404:
        return False
    
    r.raise_for_status()
    return True


def mark(key: str, meta: dict):
    """Marque une clé comme traitée dans la mémoire."""
    print(f"INFO : Marquage de la clé {key} comme traitée.")
    r = _make_request_with_retries(
        'POST',
        Settings.BLOBS_PROXY_URL,
        headers=_auth_headers(),
        json={"key": key, "meta": meta},
        timeout=20
    )
    r.raise_for_status()

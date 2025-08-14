# src/aurore/dedup.py
# Fichier de déduplication temporairement simplifié

def seen(key: str) -> bool:
    """Considère toujours un article comme nouveau."""
    print("DEBUG: La vérification de la mémoire est désactivée.")
    return False

def mark(key: str, meta: dict):
    """Ne fait rien pour l'instant."""
    print("DEBUG: Le marquage en mémoire est désactivé.")
    pass

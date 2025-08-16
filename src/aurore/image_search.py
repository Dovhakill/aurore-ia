from unsplash.api import Api
from unsplash.auth import Auth
from .config import Settings
import logging

logger = logging.getLogger("aurore")

def find_unsplash_image(query: str):
    """
    Cherche une image pertinente sur Unsplash et renvoie ses détails.
    """
    try:
        auth = Auth(Settings.UNSPLASH_ACCESS_KEY, None, None)
        unsplash = Api(auth)
        
        # La bibliothèque renvoie un objet, pas un dictionnaire simple
        search_results = unsplash.search.photos(query, per_page=1)
        
        # On vérifie la présence de résultats via l'attribut .results
        if search_results and search_results.results:
            photo = search_results.results[0]
            logger.info("Image trouvée sur Unsplash pour la recherche '%s'", query)
            
            # MODIFICATION : On accède aux données avec des points, pas des crochets
            return {
                "url": photo.urls.regular,
                "author_name": photo.user.name,
                "author_url": photo.user.links.html
            }
    except Exception as e:
        logger.warning("Erreur lors de la recherche d'image sur Unsplash : %s", e)
    
    logger.info("Aucune image trouvée sur Unsplash pour '%s'.", query)
    return None

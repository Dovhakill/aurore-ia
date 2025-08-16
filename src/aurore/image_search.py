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
        # L'authentification correcte
        auth = Auth(Settings.UNSPLASH_ACCESS_KEY, None, None)
        unsplash = Api(auth)
        
        # La recherche correcte
        search_results = unsplash.search.photos(query, per_page=1)
        
        # MODIFICATION : On revient à la lecture de dictionnaire avec les crochets
        if search_results and search_results.get("results"):
            photo = search_results["results"][0]
            logger.info("Image trouvée sur Unsplash pour la recherche '%s'", query)
            return {
                "url": photo["urls"]["regular"],
                "author_name": photo["user"]["name"],
                "author_url": photo["user"]["links"]["html"]
            }
    except Exception as e:
        logger.warning("Erreur lors de la recherche d'image sur Unsplash : %s", e)
    
    logger.info("Aucune image trouvée sur Unsplash pour '%s'.", query)
    return None

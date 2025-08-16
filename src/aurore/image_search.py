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
        
        # MODIFICATION : On enlève le paramètre 'orientation' pour une compatibilité maximale
        search_results = unsplash.search.photos(query, per_page=1)
        
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

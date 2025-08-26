import os
from pyunsplash import PyUnsplash

def find_image(query):
    """Trouve une image sur Unsplash en lien avec la query."""
    try:
        unsplash_access_key = os.environ["UNSPLASH_ACCESS_KEY"]
        if not unsplash_access_key:
            print("AVERTISSEMENT: Clé UNSPLASH_ACCESS_KEY manquante.")
            return None

        print(f"Recherche d'une image pour '{query}' sur Unsplash...")
        pu = PyUnsplash(api_key=unsplash_access_key)
        photos = pu.photos(type_='random', count=1, query=query)

        if photos and photos.entries:
            photo = photos.entries[0]
            print(f"Image trouvée : {photo.link_download}")
            return photo.url_regular
        else:
            print("Aucune image trouvée pour cette recherche.")
            return None
    except KeyError:
        print("AVERTISSEMENT: Le secret UNSPLASH_ACCESS_KEY n'est pas configuré.")
        return None
    except Exception as e:
        print(f"Erreur lors de la recherche d'image sur Unsplash : {e}")
        return None

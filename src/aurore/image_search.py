# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup

def find_image_from_source(url: str) -> str | None:
    """
    Scrape une URL pour trouver l'image principale.
    Priorise la balise meta 'og:image', la source la plus fiable.
    """
    if not url:
        return None
    
    print(f"Recherche d'image dans la source : {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Priorité n°1 : La balise Open Graph 'og:image'
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            print(f"Image trouvée depuis les métadonnées og:image : {og_image['content']}")
            return og_image['content']

        # Fallback (non implémenté pour l'instant pour rester simple)
        print("Aucune balise og:image trouvée. L'extraction d'image avancée n'est pas encore implémentée.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Erreur réseau lors de la recherche d'image : {e}")
        return None
    except Exception as e:
        print(f"Erreur inattendue dans find_image_from_source : {e}")
        return None

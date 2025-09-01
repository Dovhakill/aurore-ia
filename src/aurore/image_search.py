# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup

def find_image_from_source(google_news_url: str) -> str | None:
    if not google_news_url:
        return None
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        # --- Étape 1: Scraper la page Google News pour trouver le vrai lien ---
        print(f"Recherche du lien final depuis : {google_news_url[:70]}...")
        response_google = requests.get(google_news_url, headers=headers, timeout=10)
        response_google.raise_for_status()
        soup_google = BeautifulSoup(response_google.text, 'html.parser')
        
        # Le vrai lien est souvent dans une balise <a> avec un attribut 'jsname' ou un autre identifiant
        # On cherche le premier lien externe qui n'est pas un domaine Google.
        final_link_tag = soup_google.find('a', href=True)

        if not final_link_tag or not final_link_tag['href'].startswith('http'):
             print("Impossible d'extraire le lien final de la page Google News.")
             return None

        final_url = final_link_tag['href']
        print(f"URL finale de l'article trouvée : {final_url}")

        # --- Étape 2: Scraper la page finale pour trouver l'image ---
        print(f"Recherche d'image dans la source finale...")
        response_final = requests.get(final_url, headers=headers, timeout=10)
        response_final.raise_for_status()
        
        soup_final = BeautifulSoup(response_final.text, 'html.parser')
        
        og_image = soup_final.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image['content']
            print(f"Image trouvée depuis les métadonnées og:image : {image_url}")
            return image_url

        print("Aucune balise og:image trouvée sur la page finale.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Erreur réseau lors de la recherche d'image : {e}")
        return None
    except Exception as e:
        print(f"Erreur inattendue dans find_image_from_source : {e}")
        return None

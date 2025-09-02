# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup

def find_image_from_source(google_news_url: str) -> str | None:
    if not google_news_url:
        return None
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        # Étape 1: Suivre la redirection pour obtenir l'URL finale
        print(f"Résolution de l'URL source depuis : {google_news_url[:70]}...")
        response_redirect = requests.get(google_news_url, headers=headers, timeout=10, allow_redirects=True)
        response_redirect.raise_for_status()
        final_url = response_redirect.url
        print(f"URL finale de l'article trouvée : {final_url}")

        if "news.google.com" in final_url:
            print("La redirection n'a pas fonctionné, on tente de parser le lien...")
            soup_google = BeautifulSoup(response_redirect.text, 'html.parser')
            link_tag = soup_google.find('a', href=True)
            if link_tag:
                final_url = link_tag['href']
                print(f"URL extraite du parsing : {final_url}")
            else:
                print("Impossible d'extraire le lien final.")
                return None

        # Étape 2: Scraper la page finale pour trouver l'image
        print(f"Recherche d'image dans la source finale...")
        response_final = requests.get(final_url, headers=headers, timeout=10)
        response_final.raise_for_status()
        
        soup_final = BeautifulSoup(response_final.text, 'html.parser')
        
        og_image = soup_final.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image['content']
            print(f"Image trouvée : {image_url}")
            return image_url

        print("Aucune balise og:image trouvée sur la page finale.")
        return None

    except Exception as e:
        print(f"Erreur inattendue dans find_image_from_source : {e}")
        return None

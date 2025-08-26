import requests
from bs4 import BeautifulSoup

def find_image(article_url):
    if not article_url:
        print("AVERTISSEMENT: URL de l'article source manquante.")
        return None

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        print(f"Extraction de l'image depuis l'URL source : {article_url}")
        # allow_redirects=True va suivre le lien jusqu'à la destination finale
        response = requests.get(article_url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()

        # On utilise l'URL finale après redirection
        final_url = response.url
        print(f"URL finale après redirection : {final_url}")

        soup = BeautifulSoup(response.text, 'html.parser')

        og_image = soup.find('meta', property='og:image')

        if og_image and og_image.get('content'):
            image_url = og_image['content']
            print(f"Image 'og:image' trouvée : {image_url}")
            return image_url
        else:
            print("AVERTISSEMENT: Balise 'og:image' non trouvée dans l'article final.")
            return None

    except Exception as e:
        print(f"Erreur lors de l'extraction de l'image de la source : {e}")
        return None

import requests
from bs4 import BeautifulSoup

def find_image_from_source(article_url):
    if not article_url: return None
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(article_url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']
        return None
    except Exception as e:
        print(f"Erreur extraction image : {e}")
        return None

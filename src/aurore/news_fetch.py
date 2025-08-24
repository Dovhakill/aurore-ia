import os
from newsapi import NewsApiClient

def get_news_from_api(config):
    """Récupère les nouvelles en fonction de la configuration."""
    print(f"Récupération des articles pour la query : \"{config['news_api_query']}\"")
    try:
        newsapi_key = os.environ["NEWSAPI_KEY"]
        api_client = NewsApiClient(api_key=newsapi_key)
        
        all_articles = api_client.get_everything(
            q=config['news_api_query'],
            sources=config['news_api_sources'],
            language='fr',
            sort_by='publishedAt',
            page_size=30  # On prend une marge pour la déduplication
        )
        return all_articles.get('articles', [])
    except Exception as e:
        print(f"Erreur critique lors de la récupération des news : {e}")
        return []

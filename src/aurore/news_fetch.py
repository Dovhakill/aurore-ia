import os
from gnews import GNews

def get_news_from_api(config):
    """Récupère les nouvelles en utilisant GNews en fonction de la configuration."""
    # CORRECTION : On utilise la clé 'gnews_query' synchronisée avec config.json
    query = config['gnews_query'] 
    print(f"Récupération des articles depuis GNews pour la query : \"{query}\"")
    
    try:
        gnews_client = GNews(language='fr', country='FR')
        gnews_client.api_key = os.environ["GNEWS_API_KEY"]
        
        articles_raw = gnews_client.get_news(query)
        
        formatted_articles = []
        for article in articles_raw:
            formatted_articles.append({
                'title': article.get('title'),
                'content': article.get('description'),
                'url': article.get('url'),
                'urlToImage': article.get('image'),
            })
            
        print(f"{len(formatted_articles)} articles trouvés.")
        return formatted_articles
        
    except KeyError:
        print("Erreur critique : Le secret GNEWS_API_KEY est manquant.")
        return []
    except Exception as e:
        print(f"Erreur critique lors de la récupération des news via GNews : {e}")
        return []

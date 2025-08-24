import os
from gnews import GNews

def get_news_from_api(config):
    """Récupère les nouvelles en utilisant GNews en fonction de la configuration."""
    query = config['news_api_query'] # On utilise la même clé de config pour la query
    print(f"Récupération des articles depuis GNews pour la query : \"{query}\"")
    
    try:
        gnews_api_key = os.environ["GNEWS_API_KEY"]
        gnews_client = GNews(language='fr', country='FR', api_key=gnews_api_key)
        
        articles_raw = gnews_client.get_news(query)
        
        # On reformate la sortie de GNews pour qu'elle corresponde à ce que le reste du script attend
        formatted_articles = []
        for article in articles_raw:
            formatted_articles.append({
                'title': article.get('title'),
                'content': article.get('description'), # GNews fournit une 'description' et non le 'content' complet
                'url': article.get('url'),
                'urlToImage': article.get('image'), # GNews nomme l'image 'image'
                # D'autres champs comme 'published date' et 'source' sont disponibles si besoin
            })
            
        print(f"{len(formatted_articles)} articles trouvés.")
        return formatted_articles
        
    except Exception as e:
        print(f"Erreur critique lors de la récupération des news via GNews : {e}")
        return []

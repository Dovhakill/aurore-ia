import os
import sys
import tweepy

def post_tweet(article_title, article_url):
    print("Publication du tweet...")
    try:
        # Vérification de toutes les clés nécessaires
        consumer_key = os.environ['TWITTER_API_KEY']
        consumer_secret = os.environ['TWITTER_API_SECRET_KEY']
        access_token = os.environ['TWITTER_ACCESS_TOKEN']
        access_token_secret = os.environ['TWITTER_ACCESS_TOKEN_SECRET']
        
        # Authentification avec Tweepy v1 (API v2)
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        tweet_text = f"Nouvel article sur {os.getenv('VERTICAL_NAME', 'Horizon')}: {article_title}\n\n{article_url}"
        
        response = client.create_tweet(text=tweet_text)
        print(f"Tweet posté avec succès: https://x.com/user/status/{response.data['id']}")

    except KeyError as e:
        print(f"Erreur critique : Le secret Twitter {e} est manquant.")
        sys.exit(1) # Force l'échec du workflow
    except Exception as e:
        print(f"Erreur inattendue lors de la publication du tweet : {e}")
        sys.exit(1)

# NOUVEAU FICHIER à créer dans src/aurore/
import os
import tweepy

def post_tweet(title, url):
    try:
        consumer_key = os.environ["TWITTER_CONSUMER_KEY"]
        consumer_secret = os.environ["TWITTER_CONSUMER_SECRET"]
        access_token = os.environ["TWITTER_ACCESS_TOKEN"]
        access_token_secret = os.environ["TWITTER_ACCESS_TOKEN_SECRET"]

        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

        tweet_text = f"📰 Nouvel article par Aurore IA : {title}\n\nL'analyse complète 👇\n{url}\n\n#IA #HorizonNetwork"
        
        print("Publication du tweet...")
        client.create_tweet(text=tweet_text)
        print("Tweet publié avec succès.")
        return True
    except KeyError as e:
        print(f"Erreur : Secret Twitter manquant : {e}")
        return False
    except Exception as e:
        print(f"Erreur lors de la publication du tweet : {e}")
        return False

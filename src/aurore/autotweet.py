# -*- coding: utf-8 -*-
import os
import sys
import tweepy
import google.generativeai as genai

def generate_tweet_text(title, summary, config):
    """Génère le texte du tweet en utilisant Gemini."""
    print("Génération du texte du tweet avec Gemini...")
    try:
        gemini_api_key = os.environ["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        
        model = genai.GenerativeModel('gemini-1.5-flash')

        # On assemble le prompt multi-lignes depuis la config
        prompt_text = "".join(config['gemini_tweet_prompt'])
        prompt = prompt_text + f"\n\nTITRE: {title}\n\nRÉSUMÉ: {summary}"
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Erreur lors de la génération du tweet : {e}")
        return f"{title}"

def post_tweet(article_title, article_summary, article_url, config):
    print("Publication du tweet...")
    try:
        consumer_key = os.environ['TWITTER_API_KEY']
        consumer_secret = os.environ['TWITTER_API_SECRET_KEY']
        access_token = os.environ['TWITTER_ACCESS_TOKEN']
        access_token_secret = os.environ['TWITTER_ACCESS_TOKEN_SECRET']
        
        tweet_text = generate_tweet_text(article_title, article_summary, config)
        final_tweet = f"{tweet_text}\n\nLien vers l'analyse complète :\n{article_url}"

        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        response = client.create_tweet(text=final_tweet)
        print(f"Tweet posté avec succès: https://x.com/user/status/{response.data['id']}")

    except KeyError as e:
        print(f"Erreur critique : Le secret Twitter {e} est manquant.")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue lors de la publication du tweet : {e}")
        sys.exit(1)

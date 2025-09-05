# -*- coding: utf-8 -*-
import os
import tweepy
import google.generativeai as genai

def _compact(s: str) -> str:
    return " ".join((s or "").split())

def tweet_from_prompt(cfg: dict, title: str, summary: str, source_name: str, url: str) -> bool:
    """
    Utilise TON 'gemini_tweet_prompt' + contexte, génère 1 ligne (< 280 chars), et tweet.
    Si Twitter n'est pas configuré, on log et on sort sans échec.
    """
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET_KEY")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        print("Twitter non configuré — tweet sauté.")
        return False

    gemini_tweet_prompt = (cfg.get("gemini_tweet_prompt") or "").strip()
    brand = (cfg.get("brand_name") or "").strip()

    text = None
    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            generation_config={"temperature": 0.6, "response_mime_type": "text/plain"},
        )
        prompt = (
            f"{gemini_tweet_prompt}\n\n"
            f"Données:\n"
            f"- Titre: {title}\n"
            f"- Résumé: {summary}\n"
            f"- Source: {source_name}\n"
            f"- Lien: {url}\n\n"
            f"Rends UNE LIGNE unique. Max 280 caractères. Pas d'emojis."
        )
        resp = model.generate_content(prompt)
        text = _compact(getattr(resp, "text", "") or "")
    except Exception as e:
        print(f"WARN tweet LLM: {e}")

    if not text:
        # fallback déterministe ultra simple
        text = f"{title} ({source_name}) {url} #{brand or 'Horizon'}"
    if len(text) > 280:
        text = text[:277] + "…"

    try:
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        api = tweepy.API(auth)
        api.update_status(status=text)
        print(f"Tweet publié: {text}")
        return True
    except Exception as e:
        print(f"Tweet échoué: {e}")
        return False

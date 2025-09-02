import os
import sys
import json
import requests
from typing import Set, Dict, Optional

BLOB_KEY = "processed_urls"

def find_first_unique_article(articles: list, processed_urls: Set[str]) -> Optional[Dict]:
    for article in articles:
        if article['url'] not in processed_urls:
            return article
    return None

def get_processed_urls(config: dict) -> Set[str]:
    blob_store_url = f"https://api.netlify.com/api/v1/sites/{os.environ['NETLIFY_SITE_ID']}/blobs/{config.get('blob_store_name')}"
    headers = {"Authorization": f"Bearer {os.environ['NETLIFY_BLOBS_TOKEN']}"}
    try:
        response = requests.get(f"{blob_store_url}/{BLOB_KEY}", headers=headers)
        if response.status_code == 404:
            return set()
        response.raise_for_status()
        return set(response.json())
    except Exception as e:
        print(f"ERREUR LECTURE NETLIFY BLOBS: {e}")
        return set()

def save_processed_urls(urls_to_save: Set[str], config: dict):
    blob_store_url = f"https://api.netlify.com/api/v1/sites/{os.environ['NETLIFY_SITE_ID']}/blobs/{config.get('blob_store_name')}"
    headers = {"Authorization": f"Bearer {os.environ['NETLIFY_BLOBS_TOKEN']}"}
    try:
        response = requests.put(f"{blob_store_url}/{BLOB_KEY}", headers=headers, json=list(urls_to_save))
        response.raise_for_status() 
        print(f">>> SUCCÈS: {len(urls_to_save)} URLs sauvegardées.")
    except Exception as e:
        print(f"ERREUR SAUVEGARDE NETLIFY BLOBS: {e}")

# -*- coding: utf-8 -*-
import os
import sys
import json
import requests # <--- L'IMPORT MANQUANT EST ICI
from typing import Set, Dict, Optional

BLOB_KEY = "processed_urls"

def find_first_unique_article(articles: list, processed_urls: Set[str]) -> Optional[Dict]:
    print(f"Recherche d'un article unique parmi {len(articles)} articles trouvés...")
    for article in articles:
        if article['url'] not in processed_urls:
            print(f"Article unique trouvé : {article['title']}")
            return article
    print("Aucun nouvel article unique trouvé dans ce lot.")
    return None

def get_processed_urls(config: dict) -> Set[str]:
    blob_store_url = f"https://api.netlify.com/api/v1/sites/{os.environ['NETLIFY_SITE_ID']}/blobs/{config.get('blob_store_name')}"
    headers = {"Authorization": f"Bearer {os.environ['NETLIFY_BLOBS_TOKEN']}"}
    print("--- Début de la lecture depuis Netlify Blobs ---")
    try:
        response = requests.get(f"{blob_store_url}/{BLOB_KEY}", headers=headers)
        if response.status_code == 404:
            print("Aucune liste d'URLs existante trouvée. Démarrage avec une mémoire vide.")
            return set()
        response.raise_for_status()
        processed_list = response.json()
        print(f">>> SUCCÈS: {len(processed_list)} URLs récupérées depuis la mémoire.")
        return set(processed_list)
    except Exception as e:
        print(f"ERREUR CRITIQUE lors de la lecture depuis Netlify Blobs: {e}")
        return set()
    finally:
        print("--- Fin de la lecture depuis Netlify Blobs ---")

def save_processed_urls(urls_to_save: Set[str], config: dict):
    blob_store_url = f"https://api.netlify.com/api/v1/sites/{os.environ['NETLIFY_SITE_ID']}/blobs/{config.get('blob_store_name')}"
    headers = {"Authorization": f"Bearer {os.environ['NETLIFY_BLOBS_TOKEN']}"}
    data_payload = list(urls_to_save)
    print("--- Début de la sauvegarde dans Netlify Blobs ---")
    try:
        response = requests.put(f"{blob_store_url}/{BLOB_KEY}", headers=headers, json=data_payload)
        response.raise_for_status() 
        print(f">>> SUCCÈS: {len(data_payload)} URLs sauvegardées avec succès dans Netlify Blobs.")
    except Exception as e:
        print(f"ERREUR CRITIQUE lors de la sauvegarde dans Netlify Blobs: {e}")
    finally:
        print("--- Fin de la sauvegarde dans Netlify Blobs ---")

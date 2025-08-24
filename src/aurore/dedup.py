# REMPLACER INTÉGRALEMENT LE CONTENU DE CE FICHIER

import os
import json
import requests

def get_processed_urls(config):
    """Récupère les URLs déjà traitées depuis Netlify Blobs."""
    blob_key = config['blob_store_key']
    blobs_proxy_url = os.getenv('BLOBS_PROXY_URL')
    aurore_blobs_token = os.getenv('AURORE_BLOBS_TOKEN')

    if not blobs_proxy_url or not aurore_blobs_token:
        print("Attention: Variables pour Netlify Blobs non configurées. La déduplication sera désactivée.")
        return set()

    print(f"Récupération des URLs traitées depuis le store '{blob_key}'...")
    try:
        headers = {'Authorization': f'Bearer {aurore_blobs_token}'}
        res = requests.get(f"{blobs_proxy_url}/{blob_key}", headers=headers, timeout=10)
        if res.status_code == 404:
            print("Aucun store trouvé, création d'un nouveau set d'URLs.")
            return set()
        res.raise_for_status()
        return set(res.json())
    except requests.RequestException as e:
        print(f"Erreur de communication avec Netlify Blobs (get) : {e}")
        return set()

def save_processed_urls(urls_set, config):
    """Sauvegarde le set d'URLs mis à jour dans Netlify Blobs."""
    blob_key = config['blob_store_key']
    blobs_proxy_url = os.getenv('BLOBS_PROXY_URL')
    aurore_blobs_token = os.getenv('AURORE_BLOBS_TOKEN')

    if not blobs_proxy_url or not aurore_blobs_token:
        return

    print(f"Sauvegarde de {len(urls_set)} URLs dans le store '{blob_key}'...")
    try:
        headers = {
            'Authorization': f'Bearer {aurore_blobs_token}',
            'Content-Type': 'application/json'
        }
        res = requests.put(
            f"{blobs_proxy_url}/{blob_key}",
            headers=headers,
            data=json.dumps(list(urls_set)),
            timeout=10
        )
        res.raise_for_status()
        print("Sauvegarde réussie.")
    except requests.RequestException as e:
        print(f"Erreur de communication avec Netlify Blobs (save) : {e}")

def find_first_unique_article(articles, processed_urls_set):
    """Trouve le premier article qui n'a pas encore été traité."""
    for article in articles:
        if article.get('url') not in processed_urls_set:
            print(f"Nouvel article trouvé : {article['title']}")
            return article
    return None

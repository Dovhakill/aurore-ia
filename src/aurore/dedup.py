import os
import requests
import json
from typing import Set, Dict, Optional

# La clé unique sous laquelle nous stockons la liste des URLs dans le store
BLOB_KEY = "processed_urls"

def find_first_unique_article(articles: list, processed_urls: Set[str]) -> Optional[Dict]:
    """
    Parcourt la liste des articles et retourne le premier dont l'URL n'est pas
    dans le set des URLs déjà traitées.
    """
    print(f"Recherche d'un article unique parmi {len(articles)} articles trouvés...")
    for article in articles:
        if article['url'] not in processed_urls:
            print(f"Article unique trouvé : {article['title']}")
            return article
    print("Aucun nouvel article unique trouvé dans ce lot.")
    return None

def get_processed_urls(config: dict) -> Set[str]:
    """
    Récupère la liste des URLs déjà traitées depuis Netlify Blobs.
    Retourne un set vide si la liste n'existe pas ou en cas d'erreur.
    """
    blob_store_url = f"https://api.netlify.com/api/v1/sites/{os.environ['NETLIFY_SITE_ID']}/blobs/{config.get('blob_store_name', 'default_store')}"
    headers = {
        "Authorization": f"Bearer {os.environ['NETLIFY_BLOBS_TOKEN']}"
    }

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

    except requests.exceptions.RequestException as e:
        print(">>> ERREUR CRITIQUE: Échec de la lecture depuis Netlify Blobs.")
        if e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            print(f"Réponse de l'API: {e.response.text}")
        else:
            print(f"Erreur de connexion: {e}")
        return set()
    finally:
        print("--- Fin de la lecture depuis Netlify Blobs ---")

def save_processed_urls(urls_to_save: Set[str], config: dict):
    """
    Sauvegarde la liste complète des URLs traitées dans Netlify Blobs.
    """
    blob_store_url = f"https://api.netlify.com/api/v1/sites/{os.environ['NETLIFY_SITE_ID']}/blobs/{config.get('blob_store_name', 'default_store')}"
    headers = {
        "Authorization": f"Bearer {os.environ['NETLIFY_BLOBS_TOKEN']}"
    }
    data_payload = list(urls_to_save)

    print("--- Début de la sauvegarde dans Netlify Blobs ---")
    try:
        response = requests.put(
            f"{blob_store_url}/{BLOB_KEY}",
            headers=headers,
            json=data_payload
        )
        response.raise_for_status() 
        print(f">>> SUCCÈS: {len(data_payload)} URLs sauvegardées avec succès dans Netlify Blobs.")

    except requests.exceptions.RequestException as e:
        print(">>> ERREUR CRITIQUE: Échec de la sauvegarde dans Netlify Blobs.")
        if e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            print(f"Réponse de l'API: {e.response.text}")
        else:
            print(f"Erreur de connexion: {e}")
    finally:
        print("--- Fin de la sauvegarde dans Netlify Blobs ---")

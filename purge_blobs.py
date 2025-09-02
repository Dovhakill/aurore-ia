# -*- coding: utf-8 -*-
import os
import requests
from dotenv import load_dotenv

# --- CONFIGURATION ---
# Assure-toi que ces noms correspondent à tes stores sur Netlify
STORE_NAMES = ["aurore-libre-store", "aurore-tech-store", "aurore-memory"]
# ---------------------

def purge_store(store_name):
    print(f"\n--- Nettoyage du store : {store_name} ---")
    
    # Construction de l'URL de base pour le store
    base_url = f"https://api.netlify.com/api/v1/sites/{os.environ['NETLIFY_SITE_ID']}/blobs/{store_name}"
    headers = {
        "Authorization": f"Bearer {os.environ['NETLIFY_BLOBS_TOKEN']}"
    }

    try:
        # Étape 1 : Lister toutes les clés dans le store
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        keys_to_delete = [entry['key'] for entry in data.get('keys', [])]
        
        if not keys_to_delete:
            print("Le store est déjà vide. Rien à faire.")
            return

        print(f"Trouvé {len(keys_to_delete)} clé(s) à supprimer.")

        # Étape 2 : Supprimer chaque clé
        for key in keys_to_delete:
            print(f"Suppression de la clé : {key} ...", end='')
            delete_response = requests.delete(f"{base_url}/{key}", headers=headers)
            delete_response.raise_for_status()
            print(" OK")
            
        print(f">>> SUCCÈS : Le store '{store_name}' a été purgé.")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Le store '{store_name}' n'a pas été trouvé. On l'ignore.")
        else:
            print(f"\nERREUR HTTP: {e}")
            print(f"Réponse de l'API: {e.response.text}")
    except Exception as e:
        print(f"\nERREUR inattendue : {e}")

if __name__ == "__main__":
    print("Chargement des secrets depuis le fichier .env...")
    load_dotenv()

    if not os.getenv("NETLIFY_SITE_ID") or not os.getenv("NETLIFY_BLOBS_TOKEN"):
        print("ERREUR : Les secrets NETLIFY_SITE_ID et NETLIFY_BLOBS_TOKEN doivent être définis dans le fichier .env")
    else:
        for store in STORE_NAMES:
            purge_store(store)

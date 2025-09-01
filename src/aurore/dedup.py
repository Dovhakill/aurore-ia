import os
import requests
import json

# ... (le reste de tes imports et la fonction get_processed_urls)

def save_processed_urls(urls_to_save, config):
    """
    Sauvegarde la liste complète des URLs traitées dans Netlify Blobs.
    """
    blob_store_url = f"https://api.netlify.com/api/v1/sites/{os.environ['NETLIFY_SITE_ID']}/blobs/aurore-dedup-store"
    headers = {
        "Authorization": f"Bearer {os.environ['NETLIFY_BLOBS_TOKEN']}"
    }

    # Convertir le set en liste pour la sérialisation JSON
    data_payload = list(urls_to_save)

    print("--- Début de la sauvegarde dans Netlify Blobs ---")
    print(f"URL du store: {blob_store_url}")
    print(f"Nombre d'URLs à sauvegarder: {len(data_payload)}")

    try:
        # Nous utilisons une requête PUT pour écraser la clé avec les nouvelles données
        response = requests.put(
            f"{blob_store_url}/processed_urls",
            headers=headers,
            json=data_payload
        )

        # Lève une exception si la requête a échoué (status code 4xx ou 5xx)
        response.raise_for_status() 

        print(">>> SUCCÈS: Les URLs ont été sauvegardées avec succès dans Netlify Blobs.")
        print(f"Status Code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(">>> ERREUR CRITIQUE: Échec de la sauvegarde dans Netlify Blobs.")
        if e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            print(f"Réponse de l'API: {e.response.text}")
        else:
            print(f"Erreur de connexion: {e}")
        # On pourrait vouloir arrêter le script ici pour éviter des actions futures
        # basées sur une sauvegarde échouée. Pour l'instant, on log l'erreur.

    print("--- Fin de la sauvegarde dans Netlify Blobs ---")

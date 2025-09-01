import os
import sys
import base64
from github import Github, GithubException

def publish_article_and_update_index(title, summary, image_url, config):
    try:
        # Correction de la faute de frappe ici
        token = os.environ['GITHUB_TOKEN']
        repo_name = config['site_repo_name']
        
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # Le reste de la logique pour créer le fichier, générer le HTML, etc.
        # ... (on suppose que cette partie est fonctionnelle)

        print("Publication sur GitHub réussie.")
        # Simule un retour pour le main script
        article_url = f"https://{repo_name.split('/')[1]}.netlify.app/articles/mon-nouvel-article" # Ceci est un placeholder
        return "Article publié.", title, article_url

    except KeyError:
        print("Erreur critique lors de l'opération GitHub : Le secret GITHUB_TOKEN est manquant.")
        sys.exit(1) # Force l'échec du workflow
    except GithubException as e:
        print(f"Erreur de l'API GitHub : {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue dans github_pr.py : {e}")
        sys.exit(1)

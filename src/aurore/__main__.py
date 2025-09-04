# main.py - Version 1.1 du bot Aurore
# Inclut l'extraction d'image et la génération d'index via template.

import os
import requests
from bs4 import BeautifulSoup
from github import Github
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv

# Charger les variables d'environnement (API keys, etc.)
load_dotenv()

GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
TARGET_REPO_NAME = "Horizon-Network/horizon-tech-site" # Exemple

def get_article_details(article_url):
    """
    Extrait le titre, le résumé et l'URL de l'image d'un article source.
    Retourne un dictionnaire avec les détails, ou None en cas d'échec.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(article_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extraire le titre propre
        title = soup.find('title').text.split('|')[0].strip()

        # Extraire la description
        description_tag = soup.find('meta', attrs={'name': 'description'})
        summary = description_tag['content'] if description_tag else "Lire l'article pour en savoir plus."

        # Logique d'extraction de l'image (og:image > première image > défaut)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image['content']
        else:
            main_content = soup.find('article') or soup.find('main') or soup.body
            first_img = main_content.find('img') if main_content else None
            if first_img and first_img.get('src'):
                # Construire une URL absolue si nécessaire
                image_url = requests.compat.urljoin(article_url, first_img['src'])
            else:
                # IMPORTANT: Cette image doit exister dans le dépôt du site
                image_url = 'assets/default-image.jpg' 

        return {
            "title": title,
            "summary": summary,
            "image_url": image_url,
            "url": article_url, # L'URL source pour référence
            "date": "04/09/2025" # Placeholder, à dynamiser
        }
    except Exception as e:
        print(f"ERREUR - Impossible de parser {article_url}: {e}")
        return None

def main():
    """
    Fonction principale orchestrant le workflow du bot.
    """
    print("Démarrage du bot Aurore V1.1...")

    # --- 1. Récupération des articles (simulation) ---
    # Ici, tu aurais ton appel à l'API GNews. 
    # Pour l'exemple, on utilise une liste statique.
    articles_to_process = [
        # Remplace ça par tes vrais articles GNews
        {"title": "Un nouvel article sur l'IA", "url": "https://www.example.com/article1"},
        {"title": "La blockchain du futur", "url": "https://www.example.com/article2"},
        # ... jusqu'à 10 articles
    ]
    
    print(f"{len(articles_to_process)} articles à traiter.")
    
    # --- 2. Traitement des articles et collecte des données ---
    articles_data_for_index = []
    
    # On ajoute manuellement notre article d'enquête en tête de liste !
    # C'est la "rustine" propre pour l'intégrer au flux automatisé.
    investigation_details = get_article_details("URL_DE_TON_ARTICLE_SOURCE_POUR_LENQUETE") # Remplace par une vraie URL source
    if investigation_details:
        # On ajuste les détails pour notre article spécial
        investigation_details['title'] = "Opération 'Cochon à l'Engrais' : Démantèlement d'une arnaque crypto"
        investigation_details['url'] = "articles/enquete-arnaque-pig-butcherin.html" # Lien local
        investigation_details['date'] += " 🔹 INVESTIGATION"
        articles_data_for_index.append(investigation_details)

    for article in articles_to_process:
        details = get_article_details(article['url'])
        if details:
            # Ici, tu générerais et pousserais la page HTML de l'article individuel
            # ...
            # Puis tu ajoutes ses données à la liste pour l'index
            articles_data_for_index.append(details)

    if not articles_data_for_index:
        print("Aucune donnée d'article collectée. Arrêt.")
        return

    # --- 3. Génération et publication du nouvel index.html ---
    print("Génération du nouveau index.html...")
    
    # Connexion à GitHub
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(TARGET_REPO_NAME)

    # Récupération du contenu du template depuis le dépôt
    template_content = repo.get_contents("templates/index_template.html").decoded_content.decode('utf-8')
    
    # Configuration de Jinja2 pour charger le template depuis une chaîne
    env = Environment(loader=FileSystemLoader('.'), autoescape=select_autoescape(['html']))
    template = env.from_string(template_content)

    # Séparation des données pour le template
    featured_article = articles_data_for_index[0]
    latest_articles = articles_data_for_index[1:10] # On s'assure de n'en prendre que 9 autres

    # Rendu du HTML final
    rendered_html = template.render(
        featured_article=featured_article,
        latest_articles=latest_articles
    )

    # Publication sur GitHub
    try:
        index_file = repo.get_contents("index.html")
        repo.update_file(
            index_file.path,
            "MAJ AUTO: Reconstruction de l'index par Aurore V1.1",
            rendered_html,
            index_file.sha
        )
        print("SUCCÈS - index.html a été mis à jour dans le dépôt.")
    except Exception as e:
        print(f"ERREUR - Impossible de mettre à jour index.html: {e}")


if __name__ == "__main__":
    main()

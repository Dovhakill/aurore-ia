# -*- coding: utf-8 -*-
import os
import sys
import datetime
# import locale # <- On retire cette dépendance
from github import Github, GithubException
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup

# La ligne "locale.setlocale" est supprimée.

def slugify(text):
    """Crée un slug simple pour les noms de fichiers."""
    text = text.lower()
    return "".join(c if c.isalnum() else '-' for c in text).strip('-')

def get_existing_articles(repo):
    """Scanne le dossier 'articles' du dépôt et en extrait les métadonnées."""
    print("Scan des articles existants dans le dépôt...")
    articles = []
    try:
        contents = repo.get_contents("articles")
        for content_file in contents:
            file_content = content_file.decoded_content.decode('utf-8')
            soup = BeautifulSoup(file_content, 'html.parser')
            
            title_tag = soup.find('meta', property='og:title')
            date_tag = soup.find('meta', property='article:published_time')
            image_tag = soup.find('meta', property='og:image')

            if title_tag and date_tag:
                iso_date_str = date_tag['content']
                articles.append({
                    'title': title_tag['content'],
                    'iso_date': iso_date_str,
                    # On utilise un format numérique simple et robuste
                    'date_human': datetime.datetime.fromisoformat(iso_date_str).strftime('%d/%m/%Y'),
                    'filename': content_file.name,
                    'image_url': image_tag['content'] if image_tag else None,
                })
    except GithubException as e:
        if e.status == 404:
            print("Le dossier 'articles' n'existe pas encore. On commence avec une liste vide.")
            return []
        else:
            raise e
    print(f"{len(articles)} articles existants trouvés.")
    return articles

def publish_article_and_update_index(title, summary, image_url, config):
    try:
        token = os.environ['GITHUB_TOKEN']
        repo_name = config['site_repo_name']
        
        g = Github(token)
        repo = g.get_repo(repo_name)

        now = datetime.datetime.now()
        slug = slugify(title)
        filename = f"{now.strftime('%Y-%m-%d')}-{slug}.html"
        
        env = Environment(loader=FileSystemLoader('templates'))
        article_template = env.get_template('article.html.j2')
        article_html = article_template.render(
            title=title, 
            summary=summary, 
            image_url=image_url,
            iso_date=now.isoformat(),
            # On utilise un format numérique simple et robuste
            date_human=now.strftime('%d/%m/%Y'),
            brand_color=config['brand_color']
        )

        repo.create_file(
            f"articles/{filename}",
            f"feat: Ajout de l'article '{title}'",
            article_html,
            branch="main"
        )
        print(f"Nouvel article '{filename}' publié avec succès.")

        articles_list = get_existing_articles(repo)
        articles_list.sort(key=lambda x: x['iso_date'], reverse=True)
        latest_articles = articles_list[:10]
        
        index_template = env.get_template('index.html.j2')
        index_html = index_template.render(
            articles=latest_articles,
            brand_name=config['brand_name'],
            brand_color=config['brand_color']
        )
        
        try:
            index_file = repo.get_contents("index.html")
            repo.update_file(index_file.path, "chore: Mise à jour de la page d'accueil", index_html, index_file.sha, branch="main")
            print("Page d'accueil (index.html) mise à jour.")
        except GithubException as e:
             if e.status == 404:
                repo.create_file("index.html", "feat: Création de la page d'accueil", index_html, branch="main")
                print("Page d'accueil (index.html) créée.")

        article_url = f"https://{repo_name.split('/')[1]}.netlify.app/articles/{filename}"
        return "Article et index publiés.", title, article_url

    except KeyError as e:
        print(f"Erreur critique : Le secret {e} est manquant.")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue dans github_pr.py : {e}")
        sys.exit(1)

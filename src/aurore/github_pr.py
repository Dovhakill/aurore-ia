# -*- coding: utf-8 -*-
import os
import sys
import datetime
from github import Github, GithubException
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup

def slugify(text):
    text = text.lower()
    return "".join(c if c.isalnum() else '-' for c in text).strip('-')

def get_existing_articles(repo):
    print("Scan des articles existants via l'arbre Git...")
    articles = []
    try:
        branch = repo.get_branch("main")
        tree = repo.get_git_tree(branch.commit.sha, recursive=True).tree
        
        article_files = [item for item in tree if item.path.startswith('articles/') and item.path.endswith('.html')]
        print(f"{len(article_files)} fichiers d'articles trouvés dans l'arbre Git.")

        for item in article_files:
            file_content = repo.get_contents(item.path).decoded_content.decode('utf-8')
            soup = BeautifulSoup(file_content, 'html.parser')
            
            title_tag = soup.find('meta', property='og:title')
            date_tag = soup.find('meta', property='article:published_time')
            image_tag = soup.find('meta', property='og:image')

            if title_tag and date_tag:
                iso_date_str = date_tag['content']
                articles.append({
                    'title': title_tag['content'],
                    'iso_date': iso_date_str,
                    'date_human': datetime.datetime.fromisoformat(iso_date_str).strftime('%d/%m/%Y'),
                    'filename': os.path.basename(item.path),
                    'image_url': image_tag['content'] if image_tag else None,
                })
    except GithubException as e:
        print(f"Impossible de scanner les articles existants : {e}")
        return []
        
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
        
        # --- CORRECTION DU FORMATAGE ---
        # On transforme les sauts de ligne en balises <br>
        summary_html = summary.replace('\n', '<br>')
        
        article_html = article_template.render(
            title=title, 
            summary=summary_html, # <-- On utilise la variable corrigée
            image_url=image_url,
            iso_date=now.isoformat(),
            date_human=now.strftime('%d/%m/%Y'),
            brand_color=config['brand_color'],
            production_url=config['production_url'],
            filename=filename
        )

        repo.create_file(f"articles/{filename}", f"feat: Ajout de l'article '{title}'", article_html, branch="main")
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

        article_url = f"{config['production_url']}/articles/{filename}"
        return "Article et index publiés.", title, article_url

    except KeyError as e:
        print(f"Erreur critique : Le secret {e} est manquant.")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue dans github_pr.py : {e}")
        sys.exit(1)

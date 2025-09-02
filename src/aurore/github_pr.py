# -*- coding: utf-8 -*-
import os
import sys
import datetime
import subprocess
import tempfile
import shutil
from github import Github, GithubException
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup

def slugify(text):
    text = text.lower()
    return "".join(c if c.isalnum() else '-' for c in text).strip('-')

def get_existing_articles(repo, token):
    print("Scan des articles existants via un clone Git...")
    articles = []
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Clone du dépôt dans un dossier temporaire
            repo_url = f"https://oauth2:{token}@{repo.full_name}.git"
            subprocess.run(["git", "clone", "--depth=1", repo_url, temp_dir], check=True, capture_output=True, text=True)
            
            articles_path = os.path.join(temp_dir, "articles")
            if not os.path.isdir(articles_path):
                print("Le dossier 'articles' n'existe pas dans le dépôt cloné.")
                return []

            # Lecture des fichiers
            for filename in os.listdir(articles_path):
                if filename.endswith('.html'):
                    filepath = os.path.join(articles_path, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    soup = BeautifulSoup(content, 'html.parser')
                    title_tag = soup.find('meta', property='og:title')
                    date_tag = soup.find('meta', property='article:published_time')
                    image_tag = soup.find('meta', property='og:image')

                    if title_tag and title_tag.get('content') and date_tag and date_tag.get('content'):
                        iso_date_str = date_tag['content']
                        articles.append({
                            'title': title_tag['content'],
                            'iso_date': iso_date_str,
                            'date_human': datetime.datetime.fromisoformat(iso_date_str).strftime('%d/%m/%Y'),
                            'filename': filename,
                            'image_url': image_tag.get('content') if image_tag else None,
                        })
        except subprocess.CalledProcessError as e:
            print(f"ERREUR lors du clonage Git : {e.stderr}")
            return [] # On retourne une liste vide en cas d'échec du clonage
        except Exception as e:
            print(f"Erreur inattendue lors du scan des articles clonés : {e}")
            return []
            
    print(f"{len(articles)} articles existants parsés avec succès.")
    return articles

def publish_article_and_update_index(title, summary, image_url, config):
    try:
        token = os.environ['A_GH_TOKEN']
        repo_name = config['site_repo_name']
        g = Github(token)
        repo = g.get_repo(repo_name)

        now = datetime.datetime.now()
        slug = slugify(title)
        filename = f"{now.strftime('%Y-%m-%d')}-{slug}.html"
        
        # NOTE : On passe maintenant le token à la fonction de scan
        existing_articles = get_existing_articles(repo, token)

        new_article_data = {
            'title': title, 'iso_date': now.isoformat(),
            'date_human': now.strftime('%d/%m/%Y'), 'filename': filename,
            'image_url': image_url, 'summary_preview': summary.split('.')[0] + '.'
        }

        all_articles = [new_article_data] + existing_articles
        all_articles.sort(key=lambda x: x['iso_date'], reverse=True)
        latest_articles = all_articles[:10]
        
        env = Environment(loader=FileSystemLoader('templates'))
        
        summary_html = summary.replace('\n', '<br>')
        article_template = env.get_template('article.html.j2')
        article_html = article_template.render(
            title=title, summary=summary_html, image_url=image_url,
            iso_date=now.isoformat(), date_human=now.strftime('%d/%m/%Y'),
            brand_color=config['brand_color'], production_url=config['production_url'], filename=filename
        )
        
        index_template = env.get_template('index.html.j2')
        index_html = index_template.render(articles=latest_articles, brand_name=config['brand_name'], brand_color=config['brand_color'])

        # Mise à jour via l'API Git "Trees" (plus atomique)
        main_ref = repo.get_git_ref('heads/main')
        main_sha = main_ref.object.sha
        base_tree = repo.get_git_tree(main_sha)

        element_list = list()
        element_list.append(InputGitTreeElement(f"articles/{filename}", '100644', 'blob', article_html))
        element_list.append(InputGitTreeElement("index.html", '100644', 'blob', index_html))

        tree = repo.create_git_tree(element_list, base_tree)
        parent = repo.get_git_commit(main_sha)
        commit = repo.create_git_commit(f"feat: Ajout de l'article '{title}' et màj de l'index", tree, [parent])
        main_ref.edit(commit.sha)
        
        print(f"Nouvel article et index publiés avec succès dans un seul commit.")
        
        article_url = f"{config['production_url']}/articles/{filename}"
        return "Article et index publiés.", title, article_url

    except KeyError as e:
        print(f"Erreur critique : Le secret {e} est manquant.")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue dans github_pr.py : {e}")
        sys.exit(1)

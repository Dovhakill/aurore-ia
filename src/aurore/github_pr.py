# -*- coding: utf-8 -*-
import os
import sys
import datetime
from github import Github, GithubException
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup

def slugify(text: str) -> str:
    text = text.lower()
    return "".join(c if c.isalnum() else '-' for c in text).strip('-')

def _parse_iso_or_filename(iso_str: str | None, filename: str) -> str:
    """Retourne un ISO 8601 (UTC) sûr, à partir de la meta ou du préfixe du fichier."""
    if iso_str:
        try:
            # support 'Z' / naive
            if iso_str.endswith('Z'):
                dt = datetime.datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
            else:
                dt = datetime.datetime.fromisoformat(iso_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc).isoformat()
        except Exception:
            pass
    # fallback depuis le nom: YYYY-MM-DD-...
    try:
        d = filename[:10]
        dt = datetime.datetime.strptime(d, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

def get_existing_articles(repo):
    """Parcourt /articles et retourne une liste d'objets triables."""
    print("Scan des articles existants...")
    articles = []
    try:
        contents = repo.get_contents("articles")
        stack = contents if isinstance(contents, list) else [contents]
        while stack:
            item = stack.pop(0)
            if item.type == 'dir':
                stack.extend(repo.get_contents(item.path))
                continue
            if not item.name.lower().endswith('.html'):
                continue
            file_content = item.decoded_content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(file_content, 'html.parser')
            title_tag = soup.find('meta', attrs={'property': 'og:title'})
            date_tag = soup.find('meta', attrs={'property': 'article:published_time'})
            image_tag = soup.find('meta', attrs={'property': 'og:image'})
            title = (title_tag['content'].strip() if title_tag and title_tag.has_attr('content') else item.name)
            iso_date = _parse_iso_or_filename(date_tag['content'].strip() if date_tag and date_tag.has_attr('content') else None, item.name)
            date_human = datetime.datetime.fromisoformat(iso_date.replace('Z','+00:00')).strftime('%d/%m/%Y')
            image_url = image_tag['content'].strip() if image_tag and image_tag.has_attr('content') else None
            articles.append({
                'title': title,
                'iso_date': iso_date,
                'date_human': date_human,
                'filename': item.name,
                'image_url': image_url,
            })
    except GithubException as e:
        if e.status == 404:
            return []
        else:
            raise e
    print(f"{len(articles)} articles existants trouvés.")
    return articles

def publish_article_and_update_index(title, summary, image_url, config):
    """
    Crée un nouvel article HTML dans /articles, puis reconstruit index.html
    en listant les 10 derniers par date ISO (meta article:published_time).
    """
    try:
        # Token GitHub: GH_TOKEN (préféré) ou GITHUB_TOKEN (fallback)
        token = os.environ.get('GH_TOKEN') or os.environ['GITHUB_TOKEN']
        repo_name = config['site_repo_name']
        g = Github(token)
        repo = g.get_repo(repo_name)

        now = datetime.datetime.now(datetime.timezone.utc)
        slug = slugify(title)
        filename = f"{now.strftime('%Y-%m-%d')}-{slug}.html"

        env = Environment(loader=FileSystemLoader('templates'))

        # Rendu et création du nouvel article
        summary_html = summary.replace('\n', '<br>')
        article_template = env.get_template('article.html.j2')
        article_html = article_template.render(
            title=title,
            summary=summary_html,
            image_url=image_url,
            iso_date=now.isoformat(),
            date_human=now.strftime('%d/%m/%Y'),
            brand_name=config['brand_name'],
            brand_color=config['brand_color'],
            production_url=config['production_url'],
            filename=filename
        )
        repo.create_file(f"articles/{filename}", f"feat: Ajout de l'article '{title}'", article_html, branch="main")
        print(f"Nouvel article '{filename}' publié.")

        # Reconstruction de la liste des articles
        all_articles = get_existing_articles(repo)
        all_articles.sort(key=lambda x: x['iso_date'], reverse=True)
        latest_articles = all_articles[:10]

        # Rendu et mise à jour de l'index
        index_template = env.get_template('index.html.j2')
        index_html = index_template.render(
            articles=latest_articles,
            brand_name=config['brand_name'],
            brand_color=config['brand_color']
        )

        try:
            contents = repo.get_contents("index.html", ref="main")
            repo.update_file(contents.path, "chore: Mise à jour de la page d'accueil", index_html, contents.sha, branch="main")
            print("Page d'accueil mise à jour.")
        except GithubException as e:
            if e.status == 404:
                repo.create_file("index.html", "feat: Création de la page d'accueil", index_html, branch="main")
                print("Page d'accueil créée.")
            else:
                raise e

        article_url = f"{config['production_url'].rstrip('/')}/articles/{filename}"
        return "Article et index publiés.", title, article_url

    except KeyError as e:
        print(f"Erreur critique : Le secret {e} est manquant.")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue dans github_pr.py : {e}")
        sys.exit(1)

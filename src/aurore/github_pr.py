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
    articles = []
    try:
        contents = repo.get_contents("articles", ref="main")
        for file in contents:
            if file.type == 'file' and file.name.endswith('.html'):
                file_content = file.decoded_content.decode('utf-8')
                soup = BeautifulSoup(file_content, 'html.parser')
                title_tag = soup.find('meta', property='og:title')
                date_tag = soup.find('meta', property='article:published_time')
                if title_tag and date_tag:
                    articles.append({
                        "filename": file.name, "title": title_tag.get('content'),
                        "date_human": datetime.datetime.fromisoformat(date_tag['content']).strftime('%d/%m/%Y'),
                        "iso_date": date_tag['content']
                    })
    except GithubException as e:
        if e.status == 404: print("Dossier 'articles' non trouvé.")
        else: raise e
    print(f"{len(articles)} articles existants parsés avec succès.")
    return articles

def publish_article_and_update_index(title, summary, image_url, config):
    try:
        token = os.environ['GITHUB_TOKEN']
        repo_name = config['site_repo_name']
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        existing_articles = get_existing_articles(repo)
        now = datetime.datetime.now()
        slug = slugify(title)
        filename = f"{now.strftime('%Y-%m-%d')}-{slug}.html"

        new_article_data = {
            "filename": filename, "title": title,
            "date_human": now.strftime('%d/%m/%Y'), "iso_date": now.isoformat()
        }
        
        all_articles = [new_article_data] + existing_articles
        all_articles.sort(key=lambda x: x['iso_date'], reverse=True)
        latest_articles = all_articles[:10]
        
        env = Environment(loader=FileSystemLoader('templates'))
        article_template = env.get_template('article.html.j2')
        article_html = article_template.render(
            title=title, summary=summary.replace('\n', '<br>'), image_url=image_url,
            iso_date=now.isoformat(), date_human=now.strftime('%d/%m/%Y'),
            brand_color=config['brand_color'], production_url=config['production_url'], filename=filename
        )
        
        index_template = env.get_template('index.html.j2')
        index_html = index_template.render(articles=latest_articles, brand_name=config['brand_name'], brand_color=config['brand_color'])
        
        repo.create_file(f"articles/{filename}", f"feat: Ajout '{title}'", article_html, branch="main")
        
        try:
            contents = repo.get_contents("index.html", ref="main")
            repo.update_file(contents.path, "chore: Update index", index_html, contents.sha, branch="main")
        except GithubException as e:
            if e.status == 404: repo.create_file("index.html", "feat: Create index", index_html, branch="main")
            else: raise e
        
        article_url = f"{config['production_url']}/articles/{filename}"
        return "Article et index publiés.", title, article_url
    except Exception as e:
        print(f"Erreur inattendue dans github_pr.py : {e}")
        sys.exit(1)

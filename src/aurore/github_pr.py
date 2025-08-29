import os
import datetime
from jinja2 import Environment, FileSystemLoader
from github import Github, InputGitTreeElement, GithubException
from bs4 import BeautifulSoup

def render_html(template_name, context):
    try:
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template(template_name)
        return template.render(context)
    except Exception as e:
        print(f"Erreur lors du rendu du template {template_name} : {e}")
        return None

def publish_article_and_update_index(title, summary, image_url, config):
    repo_name = config['site_repo_name']
    try:
        g = Github(os.environ["GH_TOKEN"])
        repo = g.get_repo(repo_name)
        
        # Contexte de branding pour les templates
        brand_context = {
            "brand_name": config["brand_name"],
            "brand_color": config["brand_color"]
        }
        
        # 1. Création du HTML de l'article
        publication_date = datetime.datetime.now().strftime("%d %B %Y")
        article_context = {**brand_context, "title": title, "summary": summary, "image_url": image_url, "meta": {"description": (summary[:157] + '...') if len(summary) > 160 else summary}, "publication_date": publication_date}
        new_article_html = render_html('article.html.j2', article_context)
        if not new_article_html: return None
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ").strip()
        new_article_filename = f"articles/{timestamp}-{safe_title[:30].lower().replace(' ', '-')}.html"

        # 2. Reconstruction de l'index
        # ... (le reste de la fonction reste identique) ...

        # On passe le contexte de branding aussi à l'index
        index_context = {**brand_context, "articles": latest_articles_details}
        new_index_html = render_html('index.html.j2', index_context)
        if not new_index_html: return None

        # 3. Publication
        # ... (le reste de la fonction reste identique) ...
        
        return f"Article '{title}' publié et index mis à jour."
    except Exception as e:
        print(f"Erreur critique lors de l'opération GitHub : {e}")
        return None

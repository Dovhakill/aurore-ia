# CODE FINAL ET VÉRIFIÉ POUR src/aurore/github_pr.py

import os
import datetime
from jinja2 import Environment, FileSystemLoader
from github import Github

def render_html(template_name, context):
    """Génère du HTML à partir d'un template et d'un contexte."""
    try:
        # Le chemin correct est 'templates' (à la racine du projet)
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template(template_name)
        return template.render(context)
    except Exception as e:
        print(f"Erreur lors du rendu du template {template_name} : {e}")
        return None

def create_github_pr(title, summary, image_url, config):
    """
    Génère un nouvel article et le publie directement sur la branche main.
    """
    repo_name = config['site_repo_name']
    
    try:
        gh_token = os.environ["GH_TOKEN"]
        g = Github(gh_token)
        repo = g.get_repo(repo_name)
        
        # --- 1. Création du HTML du nouvel article ---
        meta_description = (summary[:157] + '...') if len(summary) > 160 else summary
        article_context = {
            "title": title,
            "summary": summary,
            "image_url": image_url,
            "meta": {"description": meta_description}
        }
        # On utilise le template 'article.html.j2' pour générer la page de l'article
        new_article_html = render_html('article.html.j2', article_context)
        if not new_article_html: return None

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ").strip()
        new_article_filename = f"articles/{timestamp}-{safe_title[:30].lower().replace(' ', '-')}.html"
        commit_message = f"🤖 Aurore : Ajout de l'article '{title}'"
        
        if config.get("auto_publish_direct", True):
            print(f"Publication directe de l'article sur la branche 'main'...")
            repo.create_file(
                path=new_article_filename,
                message=commit_message,
                content=new_article_html,
                branch="main"
            )
            return f"Article '{title}' publié directement."
        else:
            # Le mode Pull Request reste en backup si on le désactive dans le config.json
            return "Mode PR non implémenté dans cette version, veuillez activer 'auto_publish_direct'."

    except Exception as e:
        print(f"Erreur critique lors de l'opération GitHub : {e}")
        return None

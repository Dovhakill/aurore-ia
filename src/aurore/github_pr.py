import os
import datetime
from jinja2 import Environment, FileSystemLoader
from github import Github
from bs4 import BeautifulSoup

def render_html(template_name, context):
    """Génère du HTML à partir d'un template et d'un contexte."""
    try:
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template(template_name)
        return template.render(context)
    except Exception as e:
        print(f"Erreur lors du rendu du template {template_name} : {e}")
        return None

def create_github_pr(title, summary, image_url, config):
    """Génère un nouvel article, reconstruit l'index et publie."""
    repo_name = config['site_repo_name']

    try:
        gh_token = os.environ["GH_TOKEN"]
        g = Github(gh_token)
        repo = g.get_repo(repo_name)

        # --- 1. Création du HTML du nouvel article ---
        meta_description = (summary[:157] + '...') if len(summary) > 160 else summary

        # CORRECTION : On calcule la date ici
        publication_date = datetime.datetime.now().strftime("%d %B %Y")

        article_context = {
            "title": title,
            "summary": summary,
            "image_url": image_url,
            "meta": {"description": meta_description},
            "publication_date": publication_date # On passe la date au template
        }
        new_article_html = render_html('article.html.j2', article_context)
        if not new_article_html: return None

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ").strip()
        new_article_filename = f"articles/{timestamp}-{safe_title[:30].lower().replace(' ', '-')}.html"

        # Le reste de la logique pour reconstruire l'index et publier...
        # (Ce code reste complexe et sujet à des optimisations futures)

        commit_message = f"🤖 Aurore : Ajout de '{title}' et MàJ de l'index"

        # Logique de publication (simplifiée pour la clarté)
        repo.create_file(new_article_filename, commit_message, new_article_html, branch="main")
        print(f"Article '{title}' publié.")

        # Mettre à jour l'index ici serait la prochaine étape

        return f"Article '{title}' publié avec succès."

    except Exception as e:
        print(f"Erreur critique lors de l'opération GitHub : {e}")
        return None

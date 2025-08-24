import os
import datetime
from jinja2 import Environment, FileSystemLoader
from github import Github

def render_html(title, summary, image_url):
    """Génère le contenu HTML de l'article avec Jinja2."""
    print("Génération du fichier HTML...")
    try:
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('article.html.j2')

        # --- CORRECTION : On crée et on passe la variable 'meta' ---
        # On génère une meta description de 160 caractères max pour le SEO
        meta_description = (summary[:157] + '...') if len(summary) > 160 else summary

        meta_data = {
            "description": meta_description
        }

        return template.render(
            title=title,
            summary=summary,
            image_url=image_url,
            meta=meta_data  # On ajoute la variable manquante ici
        )
    except Exception as e:
        print(f"Erreur lors du rendu du template Jinja : {e}")
        return None

def create_github_pr(title, summary, image_url, config):
    """Crée le HTML et, selon la configuration, publie ou crée une PR."""
    html_content = render_html(title, summary, image_url)
    if not html_content:
        return None

    repo_name = config['site_repo_name']

    try:
        gh_token = os.environ["GH_TOKEN"]
        g = Github(gh_token)
        repo = g.get_repo(repo_name)

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ").strip()
        filename = f"articles/{timestamp}-{safe_title[:30].lower().replace(' ', '-')}.html"
        commit_message = f"🤖 Aurore : Ajout de l'article '{title}'"

        if config.get("auto_publish_direct", False):
            print(f"Mode autonomie activé. Push direct sur la branche 'main' de {repo_name}...")
            repo.create_file(
                path=filename,
                message=commit_message,
                content=html_content,
                branch="main"
            )
            return f"Article publié directement sur {repo_name}."
        else:
            print(f"Mode sécurisé. Création d'une Pull Request sur {repo_name}...")
            main_branch = repo.get_branch("main")
            new_branch_name = f"aurore/article-{timestamp}"
            repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=main_branch.commit.sha)

            repo.create_file(
                path=filename,
                message=commit_message,
                content=html_content,
                branch=new_branch_name
            )

            pr = repo.create_pull(
                title=f"Proposition d'article : {title}",
                body="Cet article a été généré automatiquement par Aurore.",
                head=new_branch_name,
                base="main"
            )
            return pr.html_url

    except Exception as e:
        print(f"Erreur critique lors de l'opération GitHub : {e}")
        return None

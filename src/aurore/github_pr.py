# REMPLACER INTÉGRALEMENT LE CONTENU DE CE FICHIER

import os
import datetime
from jinja2 import Environment, FileSystemLoader
from github import Github, InputGitTreeElement

def render_html(title, summary, image_url):
    """Génère le contenu HTML de l'article avec Jinja2."""
    print("Génération du fichier HTML...")
    try:
        env = Environment(loader=FileSystemLoader('src/templates'))
        # CORRECTION FINALE : On remet le bon nom de fichier '.j2'
        template = env.get_template('article.html.j2') 
        return template.render(
            title=title,
            summary=summary,
            image_url=image_url
        )
    except Exception as e:
        print(f"Erreur lors du rendu du template Jinja : {e}")
        return None

def create_github_pr(title, summary, image_url, config):
    """Crée le HTML et pousse une PR sur le repo GitHub du site configuré."""
    html_content = render_html(title, summary, image_url)
    if not html_content:
        return None

    repo_name = config['site_repo_name']
    print(f"Début du processus de commit sur le dépôt : {repo_name}")
    try:
        gh_token = os.environ["GH_TOKEN"]
        g = Github(gh_token)
        repo = g.get_repo(repo_name)

        main_branch = repo.get_branch("main")

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ").strip()
        filename = f"articles/{timestamp}-{safe_title[:30].lower().replace(' ', '-')}.html"

        element = InputGitTreeElement(path=filename, mode='100644', type='blob', content=html_content)

        tree = repo.create_git_tree([element], repo.get_git_tree(main_branch.commit.sha))
        parent_commit = repo.get_git_commit(main_branch.commit.sha)

        commit = repo.create_git_commit(
            message=f"🤖 Aurore : Ajout de l'article '{title}'",
            tree=tree,
            parents=[parent_commit]
        )

        new_branch_name = f"aurore/article-{timestamp}"
        repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=commit.sha)

        pr = repo.create_pull(
            title=f"Proposition d'article : {title}",
            body="Cet article a été généré automatiquement par Aurore. Merger pour publier.",
            head=new_branch_name,
            base="main"
        )

        print(f"Pull Request créée avec succès : {pr.html_url}")
        return pr.html_url

    except KeyError:
        print("Erreur critique : Le secret GH_TOKEN est manquant.")
        return None
    except Exception as e:
        print(f"Erreur critique lors du push sur GitHub : {e}")
        return None

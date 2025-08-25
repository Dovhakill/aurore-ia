import os
import datetime
from jinja2 import Environment, FileSystemLoader
from github import Github

def render_html(template_name, context):
    """Génère du HTML à partir d'un template et d'un contexte."""
    try:
        # Le chemin est 'templates' (à la racine)
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template(template_name)
        return template.render(context)
    except Exception as e:
        print(f"Erreur lors du rendu du template {template_name} : {e}")
        return None

def create_github_pr(title, summary, image_url, config):
    """
    Génère un nouvel article, reconstruit la page d'accueil et publie le tout.
    """
    repo_name = config['site_repo_name']
    
    try:
        # --- Initialisation ---
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
        new_article_html = render_html('article.html.j2', article_context)
        if not new_article_html: return None

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ").strip()
        new_article_filename = f"articles/{timestamp}-{safe_title[:30].lower().replace(' ', '-')}.html"
        
        # --- 2. Récupération, analyse et tri des articles existants ---
        print("Analyse des articles existants pour reconstruire la page d'accueil...")
        articles_list = []
        try:
            contents = repo.get_contents("articles")
            for content_file in contents:
                try:
                    filename = os.path.basename(content_file.path)
                    # Extrait la date du nom de fichier pour le tri
                    file_date = datetime.datetime.strptime(filename[:19], '%Y-%m-%d-%H%M%S')
                    articles_list.append({"filename": filename, "date": file_date})
                except (ValueError, IndexError):
                    continue # Ignore les fichiers qui n'ont pas le bon format de nom
        except Exception:
            print("Dossier 'articles' non trouvé ou vide, on continue avec le nouvel article.")

        # --- 3. Ajout du nouvel article à la liste ---
        articles_list.append({
            "filename": os.path.basename(new_article_filename),
            "date": datetime.datetime.now()
        })
        articles_list.sort(key=lambda x: x['date'], reverse=True)
        
        # --- 4. Reconstruction de la page d'accueil (index.html) ---
        # Pour reconstruire l'index, il nous faudrait les détails de chaque article (titre, image...).
        # C'est une opération très lourde (télécharger et parser chaque fichier).
        # On va d'abord résoudre le bug de publication, puis on implémentera cette logique.
        # Pour l'instant, on se concentre sur la publication du nouvel article.

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
            # Mode PR en backup
            # ...
            return "Mode PR non implémenté dans cette version."

    except Exception as e:
        print(f"Erreur critique lors de l'opération GitHub : {e}")
        return None

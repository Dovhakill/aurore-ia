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

def create_github_pr(title, summary, image_url, config):
    repo_name = config['site_repo_name']

    try:
        gh_token = os.environ["GH_TOKEN"]
        g = Github(gh_token)
        repo = g.get_repo(repo_name)

        # 1. Création du HTML du nouvel article
        meta_description = (summary[:157] + '...') if len(summary) > 160 else summary
        article_context = {"title": title, "summary": summary, "image_url": image_url, "meta": {"description": meta_description}}
        new_article_html = render_html('article.html.j2', article_context)
        if not new_article_html: return None

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ").strip()
        new_article_filename = f"articles/{timestamp}-{safe_title[:30].lower().replace(' ', '-')}.html"

        # 2. Récupération et analyse des articles existants
        print("Analyse des articles existants pour reconstruire l'index...")
        articles_list = []
        try:
            # CORRECTION : On gère le cas où le dossier 'articles' n'existe pas
            contents = repo.get_contents("articles")
            for file in contents:
                if file.name.endswith('.html'):
                    file_content_decoded = repo.get_contents(file.path).decoded_content.decode('utf-8')
                    soup = BeautifulSoup(file_content_decoded, 'html.parser')
                    article_title = soup.find('h1').text if soup.find('h1') else "Titre non trouvé"
                    article_image = soup.find('img')['src'] if soup.find('img') else ""
                    file_date = datetime.datetime.strptime(file.name[:19], '%Y-%m-%d-%H%M%S')

                    articles_list.append({
                        "filename": file.name, "date": file_date, "title": article_title,
                        "image_url": article_image, "date_human": file_date.strftime("%d %B %Y")
                    })
        except GithubException as e:
            if e.status == 404:
                print("Le dossier 'articles' n'existe pas encore. Il sera créé.")
            else:
                raise e

        # 3. Ajout du nouvel article et tri
        new_file_date = datetime.datetime.now()
        articles_list.append({
            "filename": os.path.basename(new_article_filename), "date": new_file_date, "title": title,
            "image_url": image_url, "date_human": new_file_date.strftime("%d %B %Y")
        })
        articles_list.sort(key=lambda x: x['date'], reverse=True)

        # 4. Reconstruction de l'index
        latest_articles = articles_list[:10]
        index_context = {"articles": latest_articles}
        new_index_html = render_html('index.html.j2', index_context)
        if not new_index_html: return "Erreur de MàJ de l'index."

        # 5. Publication
        commit_message = f"🤖 Aurore : Ajout de '{title}' et MàJ de l'index"

        # On met à jour l'index (ou on le crée)
        try:
            index_file = repo.get_contents("index.html")
            repo.update_file("index.html", commit_message, new_index_html, index_file.sha, branch="main")
            print("index.html mis à jour.")
        except GithubException as e:
            if e.status == 404:
                repo.create_file("index.html", commit_message, new_index_html, branch="main")
                print("index.html créé.")
            else:
                raise e

        # On crée le nouvel article
        repo.create_file(new_article_filename, commit_message, new_article_html, branch="main")
        print(f"Article '{title}' publié.")

        return f"Article '{title}' publié et index mis à jour."

    except Exception as e:
        print(f"Erreur critique lors de l'opération GitHub : {e}")
        return None

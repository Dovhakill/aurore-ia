import os
import datetime
from jinja2 import Environment, FileSystemLoader
from github import Github, GithubException, InputGitTreeElement
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

        # 1. Création du HTML du nouvel article
        meta_description = (summary[:157] + '...') if len(summary) > 160 else summary
        publication_date = datetime.datetime.now().strftime("%d %B %Y")
        article_context = {
            "title": title, "summary": summary, "image_url": image_url,
            "meta": {"description": meta_description}, "publication_date": publication_date
        }
        new_article_html = render_html('article.html.j2', article_context)
        if not new_article_html: return None

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ").strip()
        new_article_filename = f"articles/{timestamp}-{safe_title[:30].lower().replace(' ', '-')}.html"

        # 2. Récupération et analyse ROBUSTE des articles existants
        print("Analyse des articles existants pour reconstruire l'index...")
        articles_list = []
        try:
            contents = repo.get_contents("articles")
            for file in contents:
                if not file.name.endswith('.html'): continue

                try:
                    # CORRECTION : On ignore les fichiers avec un nom mal formaté
                    file_date = datetime.datetime.strptime(file.name[:19], '%Y-%m-%d-%H%M%S')
                    articles_list.append({"filename": file.name, "date": file_date})
                except (ValueError, IndexError):
                    print(f"AVERTISSEMENT : Fichier '{file.name}' ignoré car son nom n'est pas au format de date attendu.")
                    continue
        except GithubException as e:
            if e.status == 44:
                print("Le dossier 'articles' n'existe pas encore. Il sera créé.")
            else: raise e

        # 3. Ajout du nouvel article et tri
        new_file_date = datetime.datetime.now()
        articles_list.append({
            "filename": os.path.basename(new_article_filename), "date": new_file_date
        })
        articles_list.sort(key=lambda x: x['date'], reverse=True)

        # 4. Reconstruction de l'index
        latest_articles_details = []
        for article_data in articles_list[:10]:
            if article_data['filename'] == os.path.basename(new_article_filename):
                article_data.update({
                    'title': title, 'image_url': image_url,
                    'date_human': new_file_date.strftime("%d %B %Y")
                })
            else:
                content = repo.get_contents(f"articles/{article_data['filename']}").decoded_content.decode('utf-8')
                soup = BeautifulSoup(content, 'html.parser')
                article_data.update({
                    'title': soup.find('h1').text if soup.find('h1') else "Titre non trouvé",
                    'image_url': soup.find('img')['src'] if soup.find('img') else "",
                    'date_human': article_data['date'].strftime("%d %B %Y")
                })
            latest_articles_details.append(article_data)

        new_index_html = render_html('index.html.j2', {"articles": latest_articles_details})
        if not new_index_html: return None

        # 5. Publication
        commit_message = f"🤖 Aurore : Ajout de '{title}' et MàJ de l'index"
        main_ref = repo.get_git_ref('heads/main')
        main_sha = main_ref.object.sha
        base_tree = repo.get_git_tree(main_sha)
        element_list = [
            InputGitTreeElement(path=new_article_filename, mode='100644', type='blob', content=new_article_html),
            InputGitTreeElement(path='index.html', mode='100644', type='blob', content=new_index_html)
        ]

        tree = repo.create_git_tree(element_list, base_tree)
        parent = repo.get_git_commit(main_sha)
        commit = repo.create_git_commit(commit_message, tree, [parent])
        main_ref.edit(commit.sha)

        return f"Article '{title}' publié et index mis à jour."

    except Exception as e:
        print(f"Erreur critique lors de l'opération GitHub : {e}")
        return None

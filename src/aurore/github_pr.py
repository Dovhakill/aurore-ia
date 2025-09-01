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

        # --- 1. Préparation du nouvel article ---
        publication_date = datetime.datetime.now()
        article_context = {
            **config, "title": title, "summary": summary, "image_url": image_url,
            "meta": {"description": (summary[:157] + '...') if summary else ""},
            "publication_date": publication_date.strftime("%d %B %Y")
        }
        new_article_html = render_html('article.html.j2', article_context)
        if not new_article_html: return None

        safe_title = "".join(c for c in title if c.isalnum() or c in " ").strip()
        new_article_filename = f"articles/{publication_date.strftime('%Y-%m-%d-%H%M%S')}-{safe_title[:30].lower().replace(' ', '-')}.html"

        # --- 2. Récupération des articles existants ---
        articles_list = []
        try:
            contents = repo.get_contents("articles")
            for file in contents:
                if file.name.endswith('.html'):
                    articles_list.append({"filename": file.name, "date": datetime.datetime.strptime(file.name[:19], '%Y-%m-%d-%H%M%S')})
        except GithubException as e:
            if e.status == 404: print("Dossier 'articles' non trouvé, il sera créé.")
            else: raise e

        # --- 3. Ajout du nouvel article et tri ---
        articles_list.append({"filename": os.path.basename(new_article_filename), "date": publication_date})
        articles_list.sort(key=lambda x: x['date'], reverse=True)

        # --- 4. Reconstruction de l'index avec les détails ---
        latest_articles_details = []
        for article_data in articles_list[:10]: # On ne traite que les 10 plus récents
            # Si c'est le nouvel article, on utilise les données en mémoire
            if article_data['filename'] == os.path.basename(new_article_filename):
                article_data.update({'title': title, 'image_url': image_url, 'date_human': publication_date.strftime("%d %B %Y")})
            # Pour les anciens, on va chercher les infos dans le fichier HTML
            else:
                try:
                    content_file = repo.get_contents(f"articles/{article_data['filename']}")
                    content = content_file.decoded_content.decode('utf-8')
                    soup = BeautifulSoup(content, 'html.parser')
                    article_data.update({
                        'title': soup.find('h1').text if soup.find('h1') else "Titre non disponible",
                        'image_url': soup.find('img')['src'] if soup.find('img') else "",
                        'date_human': article_data['date'].strftime("%d %B %Y")
                    })
                except Exception as e:
                    print(f"AVERTISSEMENT : Impossible de parser l'ancien article {article_data['filename']}: {e}. Il sera listé avec des infos par défaut.")
                    article_data.update({'title': "Article", 'image_url': "", 'date_human': article_data['date'].strftime("%d %B %Y")})

            latest_articles_details.append(article_data)

        index_context = {**config, "articles": latest_articles_details}
        new_index_html = render_html('index.html.j2', index_context)
        if not new_index_html: return None

        # --- 5. Commit des 2 fichiers en une seule opération ---
        main_ref = repo.get_git_ref('heads/main')
        main_sha = main_ref.object.sha
        base_tree = repo.get_git_tree(main_sha)
        element_list = [
            InputGitTreeElement(path=new_article_filename, mode='100644', type='blob', content=new_article_html),
            InputGitTreeElement(path='index.html', mode='100644', type='blob', content=new_index_html)
        ]

        tree = repo.create_git_tree(element_list, base_tree)
        parent = repo.get_git_commit(main_sha)
        commit = repo.create_git_commit(f"🤖 Aurore : Ajout de '{title}' et MàJ de l'index", tree, [parent])
        main_ref.edit(commit.sha)

        article_url = f"https://{repo.name.replace('-site','')}.netlify.app/articles/{new_article_filename.split('/')[1]}"
        return (f"Article '{title}' publié et index mis à jour.", title, article_url)

    except Exception as e:
        print(f"Erreur critique lors de l'opération GitHub : {e}")
        return (None, None, None)

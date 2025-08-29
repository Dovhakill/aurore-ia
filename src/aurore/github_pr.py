# CODE FINAL POUR github_pr.py
import os, datetime
from jinja2 import Environment, FileSystemLoader
from github import Github, InputGitTreeElement, GithubException
from bs4 import BeautifulSoup

def render_html(template_name, context):
    try:
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template(template_name)
        return template.render(context)
    except Exception as e:
        print(f"Erreur rendu template {template_name} : {e}")
        return None

def publish_article_and_update_index(title, summary, image_url, config):
    repo_name = config['site_repo_name']
    try:
        g = Github(os.environ["GH_TOKEN"])
        repo = g.get_repo(repo_name)
        
        publication_date = datetime.datetime.now().strftime("%d %B %Y")
        article_context = {
            "brand_name": config["brand_name"], "brand_color": config["brand_color"],
            "logo_filename": config["logo_filename"], "title": title, "summary": summary,
            "image_url": image_url, "meta": {"description": (summary[:157] + '...')},
            "publication_date": publication_date
        }
        new_article_html = render_html('article.html.j2', article_context)
        if not new_article_html: return None, None
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ").strip()
        new_article_filename = f"articles/{timestamp}-{safe_title[:30].lower().replace(' ', '-')}.html"

        articles_list = []
        try:
            contents = repo.get_contents("articles")
            for file in contents:
                if file.name.endswith('.html'):
                    try:
                        articles_list.append({"filename": file.name, "date": datetime.datetime.strptime(file.name[:19], '%Y-%m-%d-%H%M%S')})
                    except (ValueError, IndexError): continue
        except GithubException as e:
            if e.status == 404: print("Dossier 'articles' non trouvé, il sera créé.")
            else: raise e

        new_file_date = datetime.datetime.now()
        articles_list.append({"filename": os.path.basename(new_article_filename), "date": new_file_date})
        articles_list.sort(key=lambda x: x['date'], reverse=True)
        
        latest_articles_details = []
        for article_data in articles_list[:10]:
            if article_data['filename'] == os.path.basename(new_article_filename):
                article_data.update({'title': title, 'image_url': image_url, 'date_human': new_file_date.strftime("%d %B %Y")})
            else:
                content = repo.get_contents(f"articles/{article_data['filename']}").decoded_content.decode('utf-8')
                soup = BeautifulSoup(content, 'html.parser')
                article_data.update({
                    'title': soup.find('h1').text if soup.find('h1') else "Titre",
                    'image_url': soup.find('img')['src'] if soup.find('img') else "",
                    'date_human': article_data['date'].strftime("%d %B %Y")
                })
            latest_articles_details.append(article_data)

        index_context = {**article_context, "articles": latest_articles_details}
        new_index_html = render_html('index.html.j2', index_context)
        if not new_index_html: return None, None

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
        
        article_url = f"https://{repo.name.replace('-site','')}.net/articles/{new_article_filename.split('/')[1]}"
        return f"Article '{title}' publié et index mis à jour.", title, article_url

    except Exception as e:
        print(f"Erreur critique lors de l'opération GitHub : {e}")
        return None, None, None

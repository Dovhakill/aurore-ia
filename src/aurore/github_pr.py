# -*- coding: utf-8 -*-
import os, sys, datetime
from github import Github, GithubException
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup

def slugify(text: str) -> str:
    text = (text or "").lower()
    return "".join(c if c.isalnum() else '-' for c in text).strip('-')

def _parse_iso(iso_str: str | None, fallback_dt: datetime.datetime) -> str:
    if iso_str:
        try:
            s = iso_str.strip()
            if s.endswith('Z'):
                dt = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
            else:
                dt = datetime.datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc).isoformat()
        except Exception:
            pass
    return fallback_dt.isoformat()

def _to_human(iso_str: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.astimezone(datetime.timezone.utc).strftime('%d/%m/%Y')
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc).strftime('%d/%m/%Y')

def get_existing_articles(repo):
    articles = []
    try:
        contents = repo.get_contents("articles")
        stack = contents if isinstance(contents, list) else [contents]
        while stack:
            item = stack.pop(0)
            if getattr(item, "type", None) == 'dir':
                stack.extend(repo.get_contents(item.path))
                continue
            if not item.name.lower().endswith('.html'):
                continue
            file_content = item.decoded_content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(file_content, 'html.parser')
            date_tag = soup.find('meta', attrs={'property': 'article:published_time'})
            iso_date = date_tag['content'].strip() if date_tag and date_tag.has_attr('content') else None
            if not iso_date:
                try:
                    d = item.name[:10]
                    dt = datetime.datetime.strptime(d, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
                    iso_date = dt.isoformat()
                except Exception:
                    iso_date = datetime.datetime.now(datetime.timezone.utc).isoformat()
            title_tag = soup.find('meta', attrs={'property': 'og:title'})
            image_tag = soup.find('meta', attrs={'property': 'og:image'})
            title = (title_tag['content'].strip() if title_tag and title_tag.has_attr('content') else item.name)
            articles.append({
                'title': title,
                'iso_date': iso_date,
                'date_human': _to_human(iso_date),
                'filename': item.name,
                'image_url': (image_tag['content'].strip() if image_tag and image_tag.has_attr('content') else None),
            })
    except GithubException as e:
        if e.status == 404:
            return []
        else:
            raise e
    return articles

def publish_article_and_update_index(title: str, summary: str, image_url: str | None, config: dict, published_at: str | None = None):
    try:
        token = os.environ.get('GH_TOKEN') or os.environ['GITHUB_TOKEN']  # A_GH_TOKEN mappé sur GH_TOKEN dans le workflow
        repo_name = config['site_repo_name']
        g = Github(token)
        repo = g.get_repo(repo_name)

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        slug = slugify(title)
        filename = f"{now_utc.strftime('%Y-%m-%d')}-{slug}.html"

        env = Environment(loader=FileSystemLoader('templates'))
        summary_html = (summary or "").replace('\n', '<br>')
        iso_pub = _parse_iso(published_at, now_utc)

        article_template = env.get_template('article.html.j2')
        article_html = article_template.render(
            title=title,
            summary=summary_html,
            image_url=image_url,
            iso_date=iso_pub,
            date_human=_to_human(iso_pub),

            brand_name=config.get('brand_name'),
            brand_color=config.get('brand_color'),
            production_url=config.get('production_url'),
            logo_filename=config.get('logo_filename'),

            filename=filename
        )
        repo.create_file(f"articles/{filename}", f"feat: article '{title}'", article_html, branch="main")
        print(f"Article publié: {filename}")

        # Index
        all_articles = get_existing_articles(repo)
        all_articles.sort(key=lambda x: x['iso_date'], reverse=True)
        latest = all_articles[:10]

        index_template = env.get_template('index.html.j2')
        index_html = index_template.render(
            articles=latest,
            brand_name=config.get('brand_name'),
            brand_color=config.get('brand_color'),
            production_url=config.get('production_url'),
            logo_filename=config.get('logo_filename'),
        )

        try:
            contents = repo.get_contents("index.html", ref="main")
            repo.update_file(contents.path, "chore: update index", index_html, contents.sha, branch="main")
            print("Index mis à jour.")
        except GithubException as e:
            if e.status == 404:
                repo.create_file("index.html", "feat: create index", index_html, branch="main")
                print("Index créé.")
            else:
                raise e

        article_url = f"{config['production_url'].rstrip('/')}/articles/{filename}"
        return "Article et index publiés.", title, article_url

    except KeyError as e:
        print(f"Secret ou clé config manquante: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur github_pr: {e}")
        sys.exit(1)

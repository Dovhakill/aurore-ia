import time
from github import Github, InputGitAuthor

def open_pr(repo_fullname: str, token: str, path: str, html: str, author_name: str, author_email: str, title: str):
    """
    Ouvre une Pull Request sur le dépôt cible avec le contenu de l'article.
    """
    gh = Github(token)
    repo = gh.get_repo(repo_fullname)
    
    # Nom de branche unique basé sur le temps
    branch_name = f"aurore/{int(time.time())}"
    
    # Récupère la branche de base (ex: "main" ou "master")
    base = repo.get_branch(repo.default_branch)
    
    # Crée la nouvelle branche à partir de la base
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base.commit.sha)

    # Message de commit
    commit_message = f"feat(aurore): Ajout article '{title}'"
    
    # MODIFICATION 1 : On crée un objet "Auteur" au bon format
    committer = InputGitAuthor(author_name, author_email)

    # MODIFICATION 2 : On crée le fichier directement, sans vérifier s'il existe
    # (car il est dans une nouvelle branche et n'existera jamais)
    repo.create_file(
        path=path, 
        message=commit_message, 
        content=html, 
        branch=branch_name, 
        committer=committer
    )

    # Crée la Pull Request
    pr_title = f"Proposition d'article : {title}"
    pr_body = "Cet article a été généré automatiquement par Aurore."
    
    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base=repo.default_branch
    )
    
    return pr.html_url

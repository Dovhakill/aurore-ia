from github import Github, InputGitAuthor
import time

def open_pr(repo_fullname: str, token: str, path: str, html: str, author_name: str, author_email: str, title: str):
    """
    Ouvre une Pull Request sur le dépôt cible et la fusionne automatiquement.
    """
    gh = Github(token)
    repo = gh.get_repo(repo_fullname)
    
    branch_name = f"aurore/{int(time.time())}"
    base = repo.get_branch(repo.default_branch)
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base.commit.sha)

    commit_message = f"feat(aurore): Ajout article '{title}'"
    committer = InputGitAuthor(author_name, author_email)

    repo.create_file(
        path=path, 
        message=commit_message, 
        content=html, 
        branch=branch_name, 
        committer=committer
    )

    pr_title = f"Proposition d'article : {title}"
    pr_body = "Cet article a été généré automatiquement par Aurore et sera fusionné dans 30 secondes."
    
    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base=repo.default_branch
    )
    print(f"INFO: Pull Request créée avec succès : {pr.html_url}")
    
    # --- SECTION D'AUTOMATISATION AJOUTÉE ---
    
    # 1. Attendre 30 secondes
    # On laisse un peu de temps aux vérifications automatiques (comme Netlify Preview) de se lancer.
    print("INFO: Attente de 30 secondes avant la fusion automatique...")
    time.sleep(30)
    
    # 2. Fusionner la Pull Request
    pr.merge()
    print("INFO: Pull Request fusionnée automatiquement avec succès !")
    
    # --- FIN DE LA SECTION D'AUTOMATISATION ---
    
    return pr.html_url

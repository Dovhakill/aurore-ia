from github import Github
import time

def open_pr(repo_fullname: str, token: str, path: str, html: str, author_name: str, author_email: str, title: str):
    gh = Github(token)
    repo = gh.get_repo(repo_fullname)
    branch = f"aurore/{int(time.time())}"
    base = repo.get_branch("main")
    repo.create_git_ref(ref=f"refs/heads/{branch}", sha=base.commit.sha)
    message = f"feat(aurore): {title}"
    try:
        existing = repo.get_contents(path, ref=branch)
        repo.update_file(path, message, html, existing.sha, branch=branch, committer={"name": author_name, "email": author_email})
    except Exception:
        repo.create_file(path, message, html, branch=branch, committer={"name": author_name, "email": author_email})
    pr = repo.create_pull(
        title=message,
        body="Article généré automatiquement par Aurore.",
        head=branch,
        base="main"
    )
    return pr.html_url
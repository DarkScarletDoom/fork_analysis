from github import Github
from datetime import datetime

# def get_forks(repoName = "medods/test-task-for-junior-backend-developer"):
#     g = Github()
#     repo = g.get_repo(repoName)
#     return repo.get_forks()

def get_forks(repo_name="medods/test-task-for-junior-backend-developer"):
    g = Github()
    repo = g.get_repo(repo_name)
    all_forks = list(repo.get_forks())
    
    # Сортируем от новых к старым и берем первые limit
    all_forks.sort(key=lambda f: f.pushed_at or datetime.min, reverse=True)
    return all_forks

from github import Github, GithubException
from github.Repository import Repository
import os
import json
from typing import Any, List, Union
from random import choices as random_choices
from datetime import datetime

gh_client = Github(os.getenv('ACCESS_TOKEN'))


def _one(obj: Union[List[Any], Any]) -> Any:
    return obj[0] if isinstance(obj, list) else obj


def get_repo(repo_name: str) -> Repository:
    return _one(gh_client.get_repo(repo_name))


def get_file_content(repo_name: str, file_path: str) -> str:
    file = _one(get_repo(repo_name).get_contents(file_path))
    return file.decoded_content.decode()


def create_file(repo_name: str, file_path: str, **kwargs):
    repo = get_repo(repo_name)
    response = repo.create_file(file_path, **kwargs)
    return response


def update_file(repo_name: str, file_path: str, **kwargs):
    repo = get_repo(repo_name)
    try:
        return repo.create_file(file_path, **kwargs)
    except GithubException as exc:
        if exc.status == 422:
            to_update = _one(repo.get_contents(file_path))
            return repo.update_file(to_update.path, sha=to_update.sha, **kwargs)
        else:
            raise exc


def rand_select(data: List) -> List:
    return random_choices(data, k=int(len(data) * 0.8))


def copy_paste_content():
    content = json.loads(
        get_file_content('thisisbud/backend-enrichment-sot', 'data/merchants/uk/v1.json')
    )
    response = update_file(
        'valeriocappuccio-bud/pygithub-experiment',
        'merchants.json',
        message=f"experiment @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        content=json.dumps(rand_select(content), indent=2),
    )
    print(f'Updated repo: {response}')


if __name__ == "__main__":
    repo = get_repo('valeriocappuccio-bud/pygithub-experiment')
    pass

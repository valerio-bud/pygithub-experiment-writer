from github import Github, GithubException
from github.Repository import Repository
import os
import json
from typing import Any, List, Union, Dict
import random
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
gh_client = Github(os.getenv('ACCESS_TOKEN'))
GhError = Union[str, List, List[Dict]]

PR_BODY = '''
## Motivation and Context

Making an experiment of making PRs via python script.
'''


def _one(obj: Union[List[Any], Any]) -> Any:
    return obj[0] if isinstance(obj, list) else obj


def get_repo(repo_name: str) -> Repository:
    return _one(gh_client.get_repo(repo_name))


def check_status(exc: GithubException):
    if exc.status != 422:
        raise


def check_already_exists(error: GhError, expected_pattern: str = 'already exist'):
    if isinstance(error, list):
        if len(error) > 1:
            raise
        message = error[0]['message']
    elif isinstance(error, dict):
        message = error['message']
    elif isinstance(error, str):
        message = error
    else:
        raise
    if expected_pattern not in message:
        raise


def get_file_content(repo_name: str, file_path: str) -> str:
    file = _one(get_repo(repo_name).get_contents(file_path))
    return file.decoded_content.decode()


def update_file(repo_name: str, file_path: str, branch: str = 'main', **kwargs):
    repo = get_repo(repo_name)
    try:
        resp = repo.create_file(file_path, **kwargs)
    except GithubException as exc:
        check_status(exc)
        check_already_exists(exc.data, '"sha" wasn\'t supplied')
        to_update = _one(repo.get_contents(file_path, ref=branch))
        resp = repo.update_file(to_update.path, sha=to_update.sha, branch=branch, **kwargs)
    logger.info(f'Updated repo: {resp}')
    return resp


def create_branch(repo_name: str, branch_name: str, source_branch: str = 'main'):
    repo = get_repo(repo_name)
    source = repo.get_branch(source_branch)
    try:
        response = repo.create_git_ref(ref='refs/heads/' + branch_name, sha=source.commit.sha)
        logger.info(f"Created branch: {response}")
    except GithubException as exc:
        check_status(exc)
        check_already_exists(exc.data)
        logger.info(f"Branch already exists: {branch_name}")


def create_pull_request(
    repo_name: str, head: str, base: str = 'main', title: str = 'New Pull Request', body: str = ""
):
    try:
        get_repo(repo_name).create_pull(title=title, head=head, base=base, body=body)
        logger.info(f"Made Pull Request for {head}")
    except GithubException as exc:
        check_status(exc)
        check_already_exists(exc.data['errors'])
        logger.info(f"Pull Request already exists for {head}")


if __name__ == "__main__":
    TARGET_REPO = 'valeriocappuccio-bud/pygithub-experiment'
    BASE_BRANCH = 'main'
    UPDATED_AT = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    FEATURE_BRANCH = f'update/{UPDATED_AT[:-9]}'

    # example of fetching data
    content = json.loads(
        get_file_content('thisisbud/backend-enrichment-sot', 'data/merchants/uk/v1.json')
    )
    new_content = json.dumps(random.choices(content, k=10), indent=2)

    create_branch(TARGET_REPO, FEATURE_BRANCH, BASE_BRANCH)
    update_file(
        TARGET_REPO,
        'merchants.json',
        message=f"experiment @ {UPDATED_AT}",
        content=new_content,
        branch=FEATURE_BRANCH,
    )
    create_pull_request(
        TARGET_REPO,
        head=FEATURE_BRANCH,
        base=BASE_BRANCH,
        title=f"Merchants Update: {UPDATED_AT}",
        body=PR_BODY,
    )

    pass

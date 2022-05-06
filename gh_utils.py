from github import Github, GithubException, InputGitTreeElement
from github.Repository import Repository
import os
from typing import Any, List, Union, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
gh_client = Github(os.getenv('ACCESS_TOKEN'))
ghRepo = Union[str, Repository]
GhError = Union[str, List, List[Dict]]


def one_(obj: Union[List[Any], Any]) -> Any:
    return obj[0] if isinstance(obj, list) else obj


def get_repo(repo: Union[str, Repository]) -> Repository:
    return repo if isinstance(repo, Repository) else one_(gh_client.get_repo(repo))


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
    file = one_(get_repo(repo_name).get_contents(file_path))
    return file.decoded_content.decode()


def get_tag_sha(repo: ghRepo, tag: str):
    repo = get_repo(repo)

    def tag_match(x) -> bool:
        return x.name == tag

    for source in repo.get_branches, repo.get_tags:
        tags = source()
        match = next(filter(tag_match, tags), None)
        if match:
            return match.commit.sha
    raise ValueError('No Tag or Branch exists with that name')


def get_folder_content(
    repo: ghRepo,
    path: str,
    branch: str = 'main',
):
    # https://sookocheff.com/post/tools/downloading-directories-of-code-from-github-using-the-github-api/
    repo = get_repo(repo)
    sha = get_tag_sha(repo, branch)
    contents = repo.get_dir_contents(path, ref=sha)
    return contents


def update_file(repo_name: str, file_path: str, branch: str = 'main', **kwargs):
    repo = get_repo(repo_name)
    try:
        resp = repo.create_file(file_path, **kwargs)
    except GithubException as exc:
        check_status(exc)
        check_already_exists(exc.data, '"sha" wasn\'t supplied')
        to_update = one_(repo.get_contents(file_path, ref=branch))
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


def make_change(
    repo: Repository, path: str, content: Any, encoding: str = "utf-8"
) -> InputGitTreeElement:
    blob = repo.create_git_blob(content, encoding)
    return InputGitTreeElement(path=path, mode='100644', type='blob', sha=blob.sha)


def commit_changes(
    repo: Repository,
    changes: List[InputGitTreeElement],
    message: str,
    branch: str = 'main',
):
    # start point
    head = repo.get_branch(branch).commit
    head_tree = repo.get_git_tree(sha=head.sha)
    # new commit
    tree = repo.create_git_tree(changes, head_tree)
    commit = repo.create_git_commit(message, tree, [head.commit])
    logger.info(f'Created {commit}')
    # push
    repo.get_git_ref('heads/' + branch).edit(sha=commit.sha)
    logger.info(f'Pushed {commit} to {branch}')

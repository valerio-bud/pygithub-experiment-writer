from github import Github, GithubException, InputGitTreeElement
from github.Repository import Repository
from github.ContentFile import ContentFile
import os
import base64
from typing import Any, List, Union, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
gh_client = Github(os.getenv('ACCESS_TOKEN'))
ghRepo = Union[str, Repository]
GhError = Union[str, List, Dict]


def one_(obj: Union[List[Any], Any]) -> Any:
    return obj[0] if isinstance(obj, list) else obj


def get_repo(repo: Union[str, Repository]) -> Repository:
    return repo if isinstance(repo, Repository) else one_(gh_client.get_repo(repo))


def check_status(exc: GithubException):
    if exc.status != 422:
        raise


def check_already_exists(error: GhError, expected_pattern: str = 'already exist'):
    # find err
    if isinstance(error, list):
        if len(error) > 1:
            raise
        err = error[0]
    else:
        err = error
    # find message
    if isinstance(err, dict):
        message = err['message']
    elif isinstance(err, str):
        message = err
    else:
        raise
    # check message
    if expected_pattern not in message:
        raise


def read_content(content: ContentFile) -> bytes:
    if content.type != 'file':
        raise TypeError(f"ContentFile.type must be 'file' to be read, not '{content.type}'")
    return content.decoded_content


def get_file_content(repo: ghRepo, file_path: str) -> bytes:
    file = one_(get_repo(repo).get_contents(file_path))
    return read_content(file)


def get_tag_sha(repo: ghRepo, tag: str):
    repo = get_repo(repo)

    def find_match(tags):
        return next((x for x in tags if x.name == tag), None)

    match = find_match(repo.get_branches())
    match = match or find_match(repo.get_tags())
    if not match:
        raise ValueError('No Tag or Branch exists with that name')
    return match.commit.sha


def get_contents(
    repo: ghRepo,
    path: str,
    ref: str = 'main',  # either branch or sha
):
    repo = get_repo(repo)
    try:
        return repo.get_contents(path.rstrip('/'), ref=ref)
    except TypeError as err:
        if err.args[0] == "argument of type 'NoneType' is not iterable":
            logger.info(f"Path does not exists: '{path}'")
            return None
        raise err


def iter_content_files(repo: ghRepo, path: str, ref: str = 'main'):
    contents = get_contents(repo, path, ref)
    try:
        for content in contents:
            if content.type == 'dir':
                yield from iter_content_files(repo, content.path, ref)
            else:
                yield content
    except TypeError:
        yield contents


def update_file(repo: ghRepo, file_path: str, branch: str = 'main', **kwargs):
    repo = get_repo(repo)
    try:
        resp = repo.create_file(file_path, **kwargs)
    except GithubException as exc:
        check_status(exc)
        check_already_exists(exc.data, '"sha" wasn\'t supplied')
        to_update = one_(repo.get_contents(file_path, ref=branch))
        resp = repo.update_file(to_update.path, sha=to_update.sha, branch=branch, **kwargs)
    logger.info(f'Updated repo: {resp}')
    return resp


def create_branch(repo: ghRepo, branch_name: str, source_branch: str = 'main'):
    repo = get_repo(repo)
    source = repo.get_branch(source_branch)
    try:
        response = repo.create_git_ref(ref='refs/heads/' + branch_name, sha=source.commit.sha)
        logger.info(f"Created branch: {response}")
    except GithubException as exc:
        check_status(exc)
        check_already_exists(exc.data)
        logger.info(f"Branch already exists: {branch_name}")


def create_pull_request(
    repo: ghRepo, head: str, base: str = 'main', title: str = 'New Pull Request', body: str = ""
):
    try:
        get_repo(repo).create_pull(title=title, head=head, base=base, body=body)
        logger.info(f"Made Pull Request for {head}")
    except GithubException as exc:
        check_status(exc)
        check_already_exists(exc.data['errors'])
        logger.info(f"Pull Request already exists for {head}")


def make_change(repo: Repository, path: str, content: bytes) -> InputGitTreeElement:
    blob = repo.create_git_blob(base64.b64encode(content).decode(), 'base64')
    return InputGitTreeElement(path=path, mode='100644', type='blob', sha=blob.sha)


def push_changes(
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

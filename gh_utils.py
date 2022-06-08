import logging
import os
import base64
from typing import Any, List, Union, Dict, Optional, Iterator, Iterable, Sequence

from github import Github, GithubException, InputGitTreeElement
from github.Repository import Repository
from github.ContentFile import ContentFile
from github.GitRef import GitRef
from github.Commit import Commit
from github.GitCommit import GitCommit
from github.Tag import Tag
from github.Branch import Branch
from github.PullRequest import PullRequest


GhRepo = Union[str, Repository]
GhError = Union[str, List, Dict]
OptionalContents = Optional[Union[ContentFile, List[ContentFile]]]
Shaable = Union[Branch, Tag]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
gh_client = Github(os.getenv('GH_TOKEN'))


def _one(obj: Any) -> Any:
    """To select first item in case the obj is a Sequence"""
    return obj[0] if isinstance(obj, Sequence) else obj


def get_repo(repo: Union[str, Repository]) -> Repository:
    """Polymorphic function to ensure a Repository type output

    Args:
        repo (Union[str, Repository]): Either name of repo or Repository object

    Returns:
        Repository: the repo to retrive
    """
    return repo if isinstance(repo, Repository) else _one(gh_client.get_repo(repo))


def _check_status(exc: GithubException, expected_status: int = 422) -> None:
    """Raise error if exc.status is not the expected one

    Args:
        exc (GithubException): object to check the status of
        expected_status (int, optional): Expected status. Different statuses will raise error.
            Defaults to 422.
    """
    if exc.status != expected_status:
        raise


def _find_error_from_response(error: GhError) -> Union[str, Dict]:
    if isinstance(error, list):
        if len(error) > 1:
            raise
        return error[0]
    return error


def _find_message_from_error(err: Union[str, Dict]) -> str:
    if isinstance(err, dict):
        return err['message']
    elif isinstance(err, str):
        return err
    raise


def _check_already_exists(error: GhError, expected_pattern: str = 'already exist') -> None:
    """Raise error if the error is not about the resource already exists

    Args:
        error (GhError): the object contaning information about the error
        expected_pattern (str, optional): the piece of text that is present in error messages when
            the resource exists already. Defaults to 'already exist'.
    """
    err = _find_error_from_response(error)
    message = _find_message_from_error(err)
    if expected_pattern not in message:
        raise


def get_contents(
    repo: GhRepo,
    path: str,
    ref: str = 'main',
) -> OptionalContents:
    """Get github object(s) in repo at the specified path and ref.

    Args:
        repo (GhRepo): the repo containing the contents
        path (str): the path in the repository
        ref (str, optional): the specific reference, either branch or sha. Defaults to 'main'.

    Raises:
        err: TypeError if the path does not exist

    Returns:
        OptionalContents: in case the exists, return the file or list of files in at that path
    """
    repo = get_repo(repo)
    try:
        return repo.get_contents(path.rstrip('/'), ref=ref)
    except TypeError as err:
        if err.args[0] == "argument of type 'NoneType' is not iterable":
            logger.info(f"Path does not exists: '{path}' at repo: {repo}")
            return None
        raise err


def read_content(content: ContentFile) -> bytes:
    """Extract the content in bytes of the ContentFile

    Args:
        content (ContentFile): github object from which to extract file content in bytes

    Raises:
        TypeError: if the content.type is not file

    Returns:
        bytes: the content of the file
    """
    if content.type != 'file':
        raise TypeError(f"ContentFile.type must be 'file' to be read, not '{content.type}'")
    return content.decoded_content


def get_file_blob(repo: GhRepo, path: str, ref: str = 'main') -> bytes:
    """Extract file content (in bytes) of the file at file_path in the repo

    Args:
        repo (GhRepo): the repo containing the file
        file_path (str): the path which the file is at (in the repo)

    Returns:
        bytes: the content of the file
    """
    content = _one(get_contents(repo, path, ref))
    return read_content(content)


def get_tag_sha(repo: GhRepo, tag: str) -> str:
    """Get the sha given either the name of the tag or branch

    Args:
        repo (GhRepo): repo to get the sha of
        tag (str): name of aither tag or branch

    Raises:
        ValueError: in case there is no branch or tag matching

    Returns:
        str: requested sha
    """
    repo = get_repo(repo)

    def find_match(tags: Iterable[Shaable]) -> Optional[Shaable]:
        return next((x for x in tags if x.name == tag), None)

    match = find_match(repo.get_branches())
    match = match or find_match(repo.get_tags())
    if not match:
        raise ValueError('No Tag or Branch exists with that name')
    return match.commit.sha


def _ensure_contents(items: OptionalContents) -> Iterable[ContentFile]:
    """Make sure the items are all valid ContentFile objects.
    It can be used to adjust upstream polymorphism to stricter downstream typing.

    Args:
        items (OptionalContents): original items object, might not be iterable or be None

    Returns:
        Iterable[ContentFile]: cleaned items with single type.
    """
    if isinstance(items, Iterable):
        contents = items
    elif items is None:
        contents = []
    else:
        contents = [items]
    return contents


def iter_content_files(repo: GhRepo, path: str, ref: str = 'main') -> Iterator[ContentFile]:
    """Iterates over content files in repo under path for specific ref

    Args:
        repo (GhRepo): repo the contents belong to
        path (str): sub path to requested contents within the repo
        ref (str, optional): Specifc branch or commit.sha to retrieve the contents from.
            Defaults to 'main'.

    Returns:
        Iterator[ContentFile]: contents of repo at specific path and ref.
    """
    contents = _ensure_contents(get_contents(repo, path, ref))
    for content in contents:
        if content.type == 'dir':
            yield from iter_content_files(repo, content.path, ref)
        else:
            yield content


def update_file(
    repo: GhRepo, file_path: str, branch: str = 'main', **kwargs
) -> Dict[str, Union[Commit, ContentFile]]:
    """Creates or update file in the repo for specific branch.

    Args:
        repo (GhRepo): repo to modify
        file_path (str): path to file to modify (or create)
        branch (str, optional): name of the branch to make the change at. Defaults to 'main'.

    Returns:
        Dict[str, Union[Commit, ContentFile]]: contains info about the commit and modified file.
    """
    repo = get_repo(repo)
    try:
        response = repo.create_file(file_path, **kwargs)
    except GithubException as exc:
        _check_status(exc)
        _check_already_exists(exc.data, '"sha" wasn\'t supplied')
        to_update = _one(repo.get_contents(file_path, ref=branch))
        response = repo.update_file(to_update.path, sha=to_update.sha, branch=branch, **kwargs)
    logger.info(f'Updated repo: {response}')
    return response


def create_branch(repo: GhRepo, branch_name: str, source_branch: str = 'main') -> GitRef:
    """Creates branch in the repo from source_branch. If branch exists

    Args:
        repo (GhRepo): repo to create new branch at
        branch_name (str): name of new branch
        source_branch (str, optional): Old branch from which to create the new one.
            Defaults to 'main'.

    Returns:
        GitRef: object containing sha for newly created (or already existing homonymous) branch.
    """
    repo = get_repo(repo)
    source = repo.get_branch(source_branch)
    try:
        ref = repo.create_git_ref(ref='refs/heads/' + branch_name, sha=source.commit.sha)
        logger.info(f'Created branch with ref: {ref} at repo: {repo}')
    except GithubException as exc:
        _check_status(exc)
        _check_already_exists(exc.data)
        ref = repo.get_git_ref('heads/' + branch_name)
        logger.info(f'Branch already exists, with ref: {ref} at repo: {repo}')
    return ref


def make_change(repo: GhRepo, path: str, content: bytes) -> InputGitTreeElement:
    """Stage change of entire file to given path of repository. The file is not committed yet.

    Args:
        repo (GhRepo): repo to change
        path (str): path of to file to change
        content (bytes): new content of file

    Returns:
        InputGitTreeElement: object that can be used to commit change to repo
    """
    repo = get_repo(repo)
    blob = repo.create_git_blob(base64.b64encode(content).decode(), 'base64')
    return InputGitTreeElement(path=path, mode='100644', type='blob', sha=blob.sha)


def push_changes(
    repo: GhRepo,
    changes: List[InputGitTreeElement],
    message: str,
    branch: str = 'main',
) -> GitCommit:
    """Commit and push the provided changes to repo branch

    Args:
        repo (GhRepo): repo to change
        changes (List[InputGitTreeElement]): changes to commit
        message (str): message of commit
        branch (str, optional): to push changes to. Defaults to 'main'.

    Returns:
        GitCommit: object containing data of commit like the sha.
    """
    repo = get_repo(repo)
    # start point
    head = repo.get_branch(branch).commit
    head_tree = repo.get_git_tree(sha=head.sha)
    # new commit
    tree = repo.create_git_tree(changes, head_tree)
    commit = repo.create_git_commit(message, tree, [head.commit])
    logger.info(f'Created {commit} at repo: {repo}')
    # push
    ref = repo.get_git_ref('heads/' + branch)
    ref.edit(sha=commit.sha)
    logger.info(f'Pushed {commit} to {branch} at repo: {repo}')
    return commit


def create_pull_request(
    repo: GhRepo, head: str, base: str = 'main', title: str = 'New Pull Request', body: str = ''
) -> PullRequest:
    """Creates pull request, if not exists already, to merge head branch to base branch.

    Args:
        repo (GhRepo): repo to make the pull request for
        head (str): to merge into the base branch
        base (str, optional): branch we are merging into. Defaults to 'main'.
        title (str, optional): title of pull request. Defaults to 'New Pull Request'.
        body (str, optional): body of pull request. Defaults to "".

    Returns:
        PullRequest: github object for pull request
    """
    repo = get_repo(repo)
    try:
        pull_req = get_repo(repo).create_pull(title=title, head=head, base=base, body=body)
        logger.info(f"Created PR '{pull_req}' to merge {head} to {base} at repo: {repo}")
    except GithubException as exc:
        _check_status(exc)
        _check_already_exists(exc.data['errors'])
        pull_req = next(iter(repo.get_pulls(base=base, head=head)))
        logger.info(f'Pull Request already exists: {pull_req} ar repo: {repo}')
    return pull_req

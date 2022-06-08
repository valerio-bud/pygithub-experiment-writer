import logging
import os
import shlex
import subprocess
from contextlib import contextmanager
from functools import wraps
from typing import Callable, Iterator, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ShellScript = Tuple[str, ...]
ShellScriptMaker = Callable[..., ShellScript]
SubProcess = Callable[..., None]


def _is_comment(line: str, log: bool = True) -> bool:
    answer = line.lstrip().startswith('#')
    if answer is True and log:
        logger.info(line.lstrip(' #'))
    return answer


def _os_popen(func: ShellScriptMaker) -> SubProcess:
    """To decorate functions returning shell scripts that use pipes |"""

    @wraps(func)
    def wrapped(*args, **kwargs):
        script = func(*args, **kwargs)
        for line in script:
            if _is_comment(line):
                continue
            stream = os.popen(line)
            # not behaving as expected yet (does not log)
            stdout = stream.read()
            bool(stdout) and logger.info(stdout)

    return wrapped


def _subprocess_popen(func: ShellScriptMaker) -> SubProcess:
    """To decorate functions returning shell scripts. Recommended if your scripts has not pipes |"""

    @wraps(func)
    def wrapped(*args, **kwargs):
        script = func(*args, **kwargs)
        for line in script:
            if _is_comment(line):
                continue
            line_args = shlex.split(line)
            with subprocess.Popen(
                line_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            ) as proc:
                # not behaving as expected yet (does not log)
                stdout = proc.stdout.read()
                bool(stdout) and logger.info(stdout)

    return wrapped


@_os_popen
def gh_login() -> ShellScript:
    return (
        'gh auth setup-git',
        '# logging in into gh',
        "yes '\n' | gh auth login",
    )


def logged_in(func: SubProcess) -> SubProcess:
    @wraps(func)
    def wrapped(*args, **kwargs):
        gh_login()
        return func(*args, **kwargs)

    return wrapped


@_os_popen
def clone_repo(repo: str, dest: str = None) -> ShellScript:
    dest = dest if (dest is not None) else repo.split('/')[-1]
    return (
        f"# cloning '{repo}' to '{dest}' (replacing existing dir if already there)'",
        f'rm -rf {dest}/',
        f'gh repo clone {repo} {dest}',
    )


@contextmanager
def in_directory(dir_: str) -> Iterator:
    original_dir = os.getcwd()
    os.chdir(dir_)
    try:
        yield
    finally:
        os.chdir(original_dir)


@_os_popen
def _commit_push(user_email: str, user_name: str, branch: str) -> ShellScript:
    """Should be run from within the clone dir. Use it within the in_directory context manager"""
    return (
        f'git config user.email "{user_email}"',
        f'git config user.name "{user_name}"',
        f'git branch {branch}',
        f'git checkout {branch}',
        'git add .',
        f'git commit -m "merchant update {branch}"',
        f'printf "{user_email}\n$GH_TOKEN" | git push --set-upstream origin {branch}',
    )


def commit_push(clone_dir: str, branch: str) -> None:
    user_name = os.getenv('GH_USER_NAME')
    user_email = os.getenv('GH_USER_EMAIL')
    with in_directory(clone_dir):
        _commit_push(user_email, user_name, branch)

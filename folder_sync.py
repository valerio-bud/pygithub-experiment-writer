from github import Github, InputGitTreeElement
from datetime import datetime
import gh_utils as ghu


def main():
    TARGET_REPO = 'valeriocappuccio-bud/pygithub-experiment'
    BASE_BRANCH = 'main'
    UPDATED_AT = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    FEATURE_BRANCH = f'update/{UPDATED_AT[:-9]}'

    repo = ghu.get_repo(TARGET_REPO)

    # changes = [
    #     ghu.make_change(repo, 'logos/hello.txt', 'hello'),
    #     ghu.make_change(repo, 'logos/world.txt', 'world'),
    # ]
    # ghu.create_branch(repo, FEATURE_BRANCH, BASE_BRANCH)
    # ghu.commit_changes(repo, changes, message="just to say hi", branch=FEATURE_BRANCH)

    ghu.get_folder_content(repo, 'logos/', branch=FEATURE_BRANCH)


if __name__ == "__main__":
    main()

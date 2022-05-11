from datetime import datetime
import gh_utils as ghu
from templates import PR_BODY


def push_hello_world(repo, branch):
    changes = [
        ghu.make_change(repo, 'logos/hello.txt', b'hello'),
        ghu.make_change(repo, 'logos/world.txt', b'world'),
    ]
    ghu.push_changes(repo, changes, message="just to say hi", branch=branch)


def main():
    TARGET_REPO = 'valeriocappuccio-bud/pygithub-experiment'
    BASE_BRANCH = 'main'
    UPDATED_AT = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    FEATURE_BRANCH = f'update/{UPDATED_AT[:-9]}'

    repo = ghu.get_repo(TARGET_REPO)

    # paths = list(Path('logos').glob('**/*.jpeg'))
    # changes = [ghu.make_change(repo, str(path), open(path, 'rb').read()) for path in paths]

    src_repo = 'thisisbud/bud-public-assets'
    src_path = 'files/bud-datasci-images/merchant_logos'
    src_contents = ghu.iter_content_files(src_repo, src_path, ref="master")

    def path_mapper(path: str) -> str:
        return path.replace(src_path, 'logos')

    def img_filter(path: str) -> bool:
        img_formats = 'jpg', 'jpeg', 'png'
        return any(path.endswith(fmt) for fmt in img_formats)

    changes = []
    for content in src_contents:
        if img_filter(content.path):
            target_path = path_mapper(content.path)
            data = ghu.read_content(content)
            change = ghu.make_change(repo, target_path, data)
            changes.append(change)
        if len(changes) > 9:
            break

    ghu.create_branch(repo, FEATURE_BRANCH, BASE_BRANCH)
    ghu.push_changes(repo, changes, message="load logos images", branch=FEATURE_BRANCH)
    ghu.create_pull_request(
        repo,
        head=FEATURE_BRANCH,
        base=BASE_BRANCH,
        title=f"Merchants Update: {UPDATED_AT}",
        body=PR_BODY,
    )


if __name__ == "__main__":
    main()

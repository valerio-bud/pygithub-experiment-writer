import json
import random
from datetime import datetime
from templates import PR_BODY
import gh_utils as ghu


if __name__ == "__main__":
    TARGET_REPO = 'valeriocappuccio-bud/pygithub-experiment'
    BASE_BRANCH = 'main'
    UPDATED_AT = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    FEATURE_BRANCH = f'update/{UPDATED_AT[:-9]}'

    # example of fetching data
    src_repo = 'thisisbud/backend-enrichment-sot'
    src_file = 'data/merchants/uk/v1.json'
    content = ghu.get_file_content(src_repo, src_file)
    new_data = json.loads(content.decode())
    new_content = json.dumps(random.choices(new_data, k=10), indent=2)

    ghu.create_branch(TARGET_REPO, FEATURE_BRANCH, BASE_BRANCH)
    ghu.update_file(
        TARGET_REPO,
        'merchants.json',
        message=f"experiment @ {UPDATED_AT}",
        content=new_content,
        branch=FEATURE_BRANCH,
    )
    ghu.create_pull_request(
        TARGET_REPO,
        head=FEATURE_BRANCH,
        base=BASE_BRANCH,
        title=f"Merchants Update: {UPDATED_AT}",
        body=PR_BODY,
    )

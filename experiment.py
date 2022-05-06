import json
import random
from datetime import datetime
import gh_utils as ghu


if __name__ == "__main__":
    TARGET_REPO = 'valeriocappuccio-bud/pygithub-experiment'
    BASE_BRANCH = 'main'
    UPDATED_AT = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    FEATURE_BRANCH = f'update/{UPDATED_AT[:-9]}'
    PR_BODY = '''
        ## Motivation and Context

        Making an experiment of making PRs via python script.
    '''

    # example of fetching data
    content = json.loads(
        ghu.get_file_content('thisisbud/backend-enrichment-sot', 'data/merchants/uk/v1.json')
    )
    new_content = json.dumps(random.choices(content, k=10), indent=2)

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

    pass

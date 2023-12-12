def default():
    task = {
        'method': 'shelloutconfig',
        'metadata': {
            'env_vars': [],
            'shelloutconfigs': ['config0-hub:::aws::codebuild-srcfile']
        }
    }
    return task

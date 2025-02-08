def default():

    task = {
        'method': 'shelloutconfig',
        'metadata': {
            'env_vars': [],
            'shelloutconfigs': ['config0-publish:::aws::docker-to-lambda']
        }
    }

    return task

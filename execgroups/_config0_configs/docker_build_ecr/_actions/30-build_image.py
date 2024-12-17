def default():

    task = {
        'method': 'shelloutconfig',
        'metadata': {
            'env_vars': [],
            'shelloutconfigs': ['config0-publish:::docker::simple_build_push']
        }
    }

    return task

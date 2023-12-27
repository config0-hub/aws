def default():

    task = {
        'method': 'shelloutconfig',
        'metadata': {
            'env_vars': [],
            'shelloutconfigs': ['config0-hub:::docker::simple_build_push']
        }
    }

    return task

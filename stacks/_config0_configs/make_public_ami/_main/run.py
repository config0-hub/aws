def run(stackargs):

    import json

    # instantiate stack
    stack = newStack(stackargs)

    stack.parse.add_required(key="name")

    stack.parse.add_required(key="config_env",
                             choices=["private","public"],
                             default="private")

    stack.parse.add_optional(key="aws_default_region",
                             default="us-east-1")

    # Add shelloutconfigs
    stack.add_shelloutconfig('config0-hub:::aws::ec2_ami')

    # Initialize
    stack.init_variables()
    stack.init_shelloutconfigs()

    # get image info
    image = stack.get_image(name=stack.name,
                            itype="ami",
                            region=stack.aws_default_region,
                            config_env=stack.config_env)

    env_vars = {"AWS_DEFAULT_REGION": stack.aws_default_region,
                "METHOD": "make_public",
                "IMAGE_ID": image}

    human_description = 'Making image_id {} public with shelloutconfig "{}"'.format(image,
                                                                                    stack.shelloutconfig)
    inputargs = {"display": True,
                 "human_description": human_description,
                 "env_vars": json.dumps(env_vars),
                 "retries": stack.retries,
                 "timeout": stack.timeout,
                 "wait_last_run": stack.wait_last_run}

    stack.ec2_ami.run(**inputargs)

    return stack.get_results()

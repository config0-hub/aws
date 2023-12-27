def run(stackargs):

    import json

    # instantiate stack
    stack = newStack(stackargs)

    stack.parse.add_required(key="name")

    stack.parse.add_required(key="config_env", 
                             choices=["private",
                                      "public"],
                             default="private")

    stack.parse.add_optional(key="aws_default_region",
                             default="us-east-1")

    stack.parse.add_optional(key="wait_last_run",
                             default=60)

    stack.parse.add_optional(key="retries",
                             default=20)

    stack.parse.add_optional(key="timeout",
                             default=1800)

    # Add shelloutconfigs
    stack.add_shelloutconfig('config0-hub:::aws::ec2_ami')

    # init the stack namespace
    stack.init_variables()

    # get image info
    image = stack.get_image(name=stack.name,
                            itype="ami",
                            region=stack.aws_default_region,
                            config_env=stack.config_env)

    env_vars = {"AWS_DEFAULT_REGION": stack.aws_default_region,
                "METHOD": "confirm",
                "IMAGE_ID": image,}

    inputargs = {"human_description": f'Verifying image_id {image} with shelloutconfig "{stack.shelloutconfig}"',
                "env_vars": json.dumps(env_vars),
                "retries": stack.retries,
                "timeout": stack.timeout,
                "wait_last_run": stack.wait_last_run,
                "display": True}

    stack.ec2_ami.run(**inputargs)

    return stack.get_results()

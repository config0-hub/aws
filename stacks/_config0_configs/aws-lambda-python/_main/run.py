def run(stackargs):

    import json

    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_required(key="config0_lambda_execgroup_name")
    stack.parse.add_required(key="lambda_name")
    stack.parse.add_required(key="s3_bucket")

    stack.parse.add_optional(key="s3_key")
    stack.parse.add_optional(key="handler", default="app.handler")
    stack.parse.add_optional(key="runtime", default="python3.9")
    stack.parse.add_optional(key="memory_size", default="256")
    stack.parse.add_optional(key="lambda_timeout", default="900")
    stack.parse.add_optional(key="lambda_layers")
    stack.parse.add_optional(key="policy_template_hash")

    stack.parse.add_optional(key="aws_default_region", default="us-east-1")
    stack.parse.add_optional(key="lambda_env_vars_hash")
    stack.parse.add_optional(key="cloud_tags_hash")
    stack.parse.add_optional(key="stateful_id", default="_random")
    stack.parse.add_optional(key="debug")

    # declare execution groups
    stack.add_execgroup("config0-hub:::aws::py_to_lambda")

    # add substack
    stack.add_substack('config0-hub:::aws_lambda')

    # initialize variables
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    # ref 5490734650346
    stack.add_execgroup("{} {}".format(stack.config0_lambda_execgroup_name,
                                       stack.py_to_lambda.name),
                        "buildgroups",
                        overide=True)

    # reset exec groups
    stack.reset_execgroups()

    env_vars = {"LAMBDA_PKG_NAME": stack.lambda_name}
    env_vars["S3_BUCKET"] = stack.s3_bucket
    env_vars["stateful_id".upper()] = stack.stateful_id
    env_vars["WORKING_SUBDIR"] = "var/tmp/lambda"
    if stack.get_attr("debug"):
        env_vars["CONFIG0_ENHANCED_LOGGING"] = "True"

    inputargs = {"name": stack.lambda_name}
    inputargs["env_vars"] = json.dumps(env_vars)
    inputargs["working_dir"] = "execgroup"  # this reset working directory to be same as execuction group

    if hasattr(stack, "cloud_tags_hash") and stack.cloud_tags_hash:
        inputargs["cloud_tags_hash"] = stack.cloud_tags_hash

    stack.buildgroups.insert(**inputargs)

    # create lambda function
    if not stack.get_attr("s3_key"):
        s3_key = "{}.zip".format(stack.lambda_name)
    else:
        s3_key = stack.s3_key

    arguments = {"s3_key": s3_key,
                 "lambda_name": stack.lambda_name}

    arguments["s3_bucket"] = stack.s3_bucket
    arguments["handler"] = stack.handler
    arguments["runtime"] = stack.runtime
    arguments["memory_size"] = stack.memory_size
    arguments["lambda_timeout"] = stack.lambda_timeout
    arguments["aws_default_region"] = stack.aws_default_region

    if stack.get_attr("policy_template_hash"):
        arguments["policy_template_hash"] = stack.policy_template_hash

    if stack.get_attr("lambda_layers"):
        arguments["lambda_layers"] = stack.lambda_layers

    if stack.get_attr("lambda_env_vars_hash"):
        arguments["lambda_env_vars_hash"] = stack.lambda_env_vars_hash

    if hasattr(stack, "cloud_tags_hash") and stack.cloud_tags_hash:
        arguments["cloud_tags_hash"] = stack.cloud_tags_hash

    if stack.get_attr("stateful_id"):
        # this is downstream for aws_lambda
        arguments["stateful_id"] = stack.stateful_id

    inputargs = {"arguments": arguments}
    inputargs["automation_phase"] = "infrastructure"
    inputargs["human_description"] = 'Create lambda function for {}'.format(
        stack.lambda_name)
    stack.aws_lambda.insert(display=True, **inputargs)

    return stack.get_results()

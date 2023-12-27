def run(stackargs):
    import json
    import os

    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_required(key="config0_lambda_execgroup_name")

    stack.parse.add_required(key="lambda_name",
                             tags="arguments",
                             types="str")

    stack.parse.add_required(key="s3_bucket",
                             tags="env_vars,arguments",
                             types="str")

    stack.parse.add_optional(key="s3_key",
                             tags="arguments",
                             types="str")

    stack.parse.add_optional(key="handler",
                             tags="arguments",
                             types="str",
                             default="app.handler")

    stack.parse.add_optional(key="runtime",
                             tags="arguments",
                             types="str",
                             default="nodejs12.x")

    stack.parse.add_optional(key="memory_size",
                             tags="arguments",
                             types="int",
                             default="128")

    stack.parse.add_optional(key="lambda_timeout",
                             tags="arguments",
                             types="int",
                             default="300")

    stack.parse.add_optional(key="lambda_layers",
                             tags="arguments",
                             types="str")

    stack.parse.add_optional(key="policy_template_hash",
                             tags="arguments",
                             types="str")

    stack.parse.add_optional(key="aws_default_region",
                             tags="arguments",
                             types="str",
                             default="us-east-1")

    stack.parse.add_optional(key="lambda_env_vars_hash",
                             tags="arguments",
                             types="str")

    stack.parse.add_optional(key="cloud_tags_hash",
                             tags="arguments",
                             types="str")

    stack.parse.add_optional(key="stateful_id",
                             tags="env_vars,arguments",
                             types="str",
                             default="_random")

    stack.parse.add_optional(key="debug")

    # declare execution groups
    stack.add_execgroup("config0-hub:::aws::nodejs_to_lambda")

    # add substack
    stack.add_substack('config0-hub:::aws_lambda')

    # initialize variables
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    # ref 5490734650346
    stack.add_execgroup("{} {}".format(stack.config0_lambda_execgroup_name,
                                       stack.nodejs_to_lambda.name),
                        "buildgroups",
                        overide=True)

    # reset exec groups
    stack.reset_execgroups()

    env_vars = stack.get_tagged_vars(tag="env_vars",
                                     output="dict")

    env_vars.update({"LAMBDA_PKG_NAME": stack.lambda_name,
                     "WORKING_SUBDIR": "var/tmp/lambda"})

    if stack.get_attr("debug"):
        env_vars["CONFIG0_ENHANCED_LOGGING"] = "True"

    inputargs = {"name": stack.lambda_name,
                 "env_vars": json.dumps(env_vars),
                 "working_dir": "execgroup"}

    if stack.get_attr("cloud_tags_hash"):
        inputargs["cloud_tags_hash"] = stack.cloud_tags_hash

    stack.buildgroups.insert(**inputargs)

    # create lambda function
    if not stack.get_attr("s3_key"):
        stack.set_variable("s3_key",
                           "{}.zip".format(stack.lambda_name),
                           tags="arguments",
                           types="str")

    arguments = stack.get_tagged_vars(tag="arguments",
                                      output="dict")

    inputargs = {"arguments": arguments,
                 "automation_phase": "infrastructure",
                 "human_description": 'Create lambda function for {}'.format(stack.lambda_name)}

    stack.aws_lambda.insert(display=True,
                            **inputargs)

    return stack.get_results()

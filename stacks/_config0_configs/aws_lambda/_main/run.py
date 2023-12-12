from config0_publisher.terraform import TFConstructor


def _default_policy():

    policy = {"Version": "2012-10-17",
              "Statement": [{"Action": ["logs:CreateLogGroup",
                                        "logs:CreateLogStream",
                                        "logs:PutLogEvents"],
                             "Resource": "arn:aws:logs:*:*:*",
                             "Effect": "Allow"}]
              }

    return policy


def _assume_default_policy():

    policy = {"Version": "2012-10-17",
              "Statement": [{"Action": "sts:AssumeRole",
                             "Principal": {"Service": "lambda.amazonaws.com"},
                             "Effect": "Allow",
                             "Sid": ""}]
              }

    return policy


def run(stackargs):

    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_required(key="s3_bucket",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_required(key="lambda_name",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="handler",
                             default="app.handler",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="runtime",
                             default="python3.9",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="memory_size",
                             default="256",
                             tags="tfvar",
                             types="int")

    stack.parse.add_optional(key="lambda_timeout",
                             default="900",
                             tags="tfvar",
                             types="int")

    stack.parse.add_optional(key="lambda_layers",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="s3_key",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="policy_template_hash",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="lambda_env_vars_hash",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="aws_default_region",
                             default="eu-west-1",
                             tags="tfvar,resource,db,runtime_settings",
                             types="str")

    # Add execgroup
    stack.add_execgroup("config0-hub:::aws::add_lambda", "tf_execgroup")

    # Add substack
    stack.add_substack('config0-hub:::tf_executor')

    # Initialize Variables in stack
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    if not stack.get_attr("s3_key"):
        stack.set_variable("s3_key",
                           "{}.zip".format(stack.lambda_name),
                           tags="tfvar",
                           types="str")

    if stack.get_attr("lambda_env_vars_hash"):
        lambda_env_vars = stack.b64_decode(stack.lambda_env_vars_hash)
    else:
        lambda_env_vars = {}

    stack.set_variable("lambda_env_vars",
                       lambda_env_vars,
                       tags="tfvar",
                       types="str,dict")

    tf = TFConstructor(stack=stack,
                       provider="aws",
                       execgroup_name=stack.tf_execgroup.name,
                       resource_name=stack.lambda_name,
                       resource_type="aws_lambda",
                       terraform_type="aws_lambda_function")

    tf.include(maps={"id": "arn",
                     "name": "function_name"})

    tf.include(keys=["function_name",
                     "handler",
                     "invoke_arn",
                     "arn",
                     "layers",
                     "memory_size",
                     "role",
                     "runtime",
                     "s3_bucket",
                     "s3_key",
                     "timeout"])

    tf.output(keys=["s3_key",
                    "s3_bucket",
                    "memory_size",
                    "role",
                    "runtime",
                    "handler",
                    "invoke_arn",
                    "function_name",
                    "layers",
                    "timeout",
                    "arn",
                    "resource_type"])

    # finalize the tf_executor
    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()

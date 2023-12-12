from config0_publisher.terraform import TFConstructor


def run(stackargs):

    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_required(key="role_name",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_required(key="iam_instance_profile",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_required(key="iam_role_policy_name",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="policy",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="assume_policy",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="aws_default_region",
                             default="eu-west-1",
                             tags="tfvar,resource,db,runtime_settings",
                             types="str")

    stack.add_execgroup("config0-hub:::aws::iam-role", "tf_execgroup")

    # Add substack
    stack.add_substack('config0-hub:::tf_executor')

    # Initialize
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    # policy as b64 encoded
    if not stack.get_attr("policy"):

        allow = "*/s3:*,ecr:*,kms:*,ec2:*,ssm:*,eks:*,rds:*,dynamodb:*,iam:*"
        _resources, _actions = allow.split("/")

        resources = _resources.split(",")
        actions = _actions.split(",")

        allowed = {"Version": "2012-10-17",
                   "Statement": [{"Action": actions,
                                  "Effect": "Allow",
                                  "Resource": resources}]}

        stack.set_variable("policy", 
                           stack.b64_encode(allowed), 
                           tags="tfvar", 
                           types="str")

    # assume_policy
    if not stack.get_attr("assume_policy"):
        assume_policy = {"Version": "2012-10-17",
                         "Statement": [{"Action": "sts:AssumeRole",
                                        "Principal": {"Service": "ec2.amazonaws.com"},
                                        "Effect": "Allow",
                                        "Sid": ""}]}

        stack.set_variable("assume_policy", 
                           stack.b64_encode(assume_policy), 
                           tags="tfvar", 
                           types="str")

    tf = TFConstructor(stack=stack,
                       provider="aws",
                       execgroup_name=stack.tf_execgroup.name,
                       resource_name=stack.role_name,
                       resource_type="iam_instance_profile",
                       terraform_type="aws_iam_instance_profile")

    tf.include(maps={"id": "unique_id"})

    tf.include(keys=["arn",
                     "name",
                     "unique_id",
                     "role"])

    tf.output(keys=["id",
                    "arn",
                    "name",
                    "role",
                    "unique_id",
                    "resource_type"])

    # finalize the tf_executor
    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()

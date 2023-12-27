from config0_publisher.terraform import TFConstructor


def run(stackargs):
    import random

    # instantiate authoring stack
    stack = newStack(stackargs)

    stack.parse.add_required(key="subnet_ids")

    stack.parse.add_required(key="hostname",
                             tags="tfvar,db",
                             default="_random",
                             types="str")

    stack.parse.add_required(key="key_name",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="ami_filter",
                             default='ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-*',
                             tags="tfvar",
                             types="str")

    # default is canonical
    stack.parse.add_optional(key="ami_owner",
                             default='099720109477',
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="instance_type",
                             default="t2.micro",
                             tags="tfvar,db",
                             types="str")

    # we need to use string value for true b/c tfvar
    stack.parse.add_optional(key="associate_public_ip_address",
                             default="true",
                             tags="tfvar",
                             types="bool")

    stack.parse.add_optional(key="volume_type",
                             default="gp2",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="volume_size",
                             default="20",
                             tags="tfvar",
                             types="int")

    stack.parse.add_optional(key="iam_instance_profile",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="sg_id",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="ami",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="aws_default_region",
                             default="eu-west-1",
                             tags="tfvar,resource,db,runtime_settings",
                             types="str")

    # tf_execgroup alias isn't necessary, but it
    # provides some standardization across tf stacks
    stack.add_execgroup("config0-hub:::aws::ec2_server",
                        "tf_execgroup")

    # Add substack
    stack.add_substack('config0-hub:::tf_executor')

    # initialize
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    # random element for subnet_id
    avail_subnets = stack.to_list(stack.subnet_ids)
    subnet_element = random.randrange(len(avail_subnets) - 1)

    stack.set_variable("subnet_id",
                       avail_subnets[subnet_element],
                       tags="tfvar,db",
                       types="str")

    # use the terraform constructor (helper)
    # but this is optional
    tf = TFConstructor(stack=stack,
                       execgroup_name=stack.tf_execgroup.name,
                       provider="aws",
                       resource_name=stack.hostname,
                       resource_type="server",
                       terraform_type="aws_instance")

    # terraform resource keys
    # to transfer to db for querying
    tf.include(keys=["id",
                     "ami",
                     "arn",
                     "private_dns",
                     "private_ip",
                     "public_dns",
                     "public_ip"])

    # terraform resource keys
    # to map for ease of query in db
    tf.include(maps={"_id": "id",
                     "region": "aws_default_region"})

    # resource output to show
    # on saas ui
    tf.output(keys=["id",
                    "ami",
                    "arn",
                    "private_ip",
                    "public_ip"])

    # finalize the tf_executor
    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()

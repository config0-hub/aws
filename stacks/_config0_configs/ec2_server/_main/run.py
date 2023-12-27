# dup 4523453245432523
def _eval_tags_labels(stack):

    import json

    stack.set_variable("tags", None)

    if stack.get_attr("cloud_tags_hash"):

        cloud_tags = stack.b64_decode(stack.cloud_tags_hash)

        stack.set_variable("tags",
                           json.dumps(cloud_tags),
                           tags="env_var,ec2_server,ebs,ebs_config")
    else:
        cloud_tags = None

    if not cloud_tags:
        return

    if not stack.get_attr("labels"):
        stack.set_variable("labels",
                           cloud_tags,
                           tags="env_var,ec2_server,ebs,ebs_config")
        return

    if not isinstance(stack.labels, dict):
        stack.set_variable("labels",
                           stack.to_json(stack.labels),
                           tags="env_var,ec2_server,ebs,ebs_config",
                           types="dict")

    for _k, _v in cloud_tags.items():
        stack.labels[_k] = _v

def run(stackargs):

    import json

    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_required(key="hostname",
                             tags="env_var,ebs,ebs_config",
                             default="_random",
                             types="str")

    stack.parse.add_required(key="ssh_key_name",
                             tags="ebs_config",
                             types="str")

    stack.parse.add_optional(key="ami_filter",
                             default='Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-*',
                             types="str")

    # default is canonical
    stack.parse.add_optional(key="ami_owner",
                             default='099720109477',
                             types="str")

    stack.parse.add_optional(key="instance_type",
                             default="t2.micro",
                             tags="env_var",
                             types="str")

    stack.parse.add_optional(key="aws_default_region",
                             default="eu-west-1",
                             tags="env_var,ebs,ebs_config",
                             types="str")

    # subnet_id
    stack.parse.add_required(key="subnet_id",
                             tags="env_var",
                             types="str")

    # security groups csv
    stack.parse.add_optional(key="security_group_ids",
                             tags="env_var",
                             types="str")

    # security groups csv
    stack.parse.add_optional(key="security_groups",
                             tags="env_var",
                             types="str")

    # Image will be filtering or an ami
    stack.parse.add_optional(key="ami",
                             types="str")

    stack.parse.add_optional(key="disksize",
                             default="30",
                             tags="env_var",
                             types="int")

    # spot request
    stack.parse.add_optional(key="spot",
                             types="bool",
                             tags="env_var")

    stack.parse.add_optional(key="spot_max_price",
                             types="int",
                             tags="env_var")

    stack.parse.add_optional(key="spot_type",
                             types="str",
                             tags="env_var",
                             default="persistent")

    # misc
    stack.parse.add_optional(key="iam_instance_profile",
                             tags="env_var",
                             types="str")

    stack.parse.add_optional(key="user_data",
                             types="str",
                             tags="env_var")

    # identification

    # labels will be used for config0 resource
    stack.parse.add_optional(key="labels")

    stack.parse.add_optional(key="cloud_tags_hash",
                             types="str",
                             tags="ebs")

    # extra disk
    stack.parse.add_optional(key="volume_name",
                             types="str",
                             tags="ebs,ebs_config")

    stack.parse.add_optional(key="volume_size",
                             types="int",
                             tags="ebs")

    stack.parse.add_optional(key="volume_mountpoint",
                             types="str",
                             tags="ebs,ebs_config")

    stack.parse.add_optional(key="volume_fstype",
                             types="str",
                             tags="ebs,ebs_config")

    # the config network to configure the volume
    stack.parse.add_optional(key="config_network",
                             choices=["private", "public"],
                             types="str",
                             tags="ebs_config",
                             default="private")

    # Add shelloutconfig dependencies
    stack.add_shelloutconfig('config0-hub:::aws::ec2_server',
                             "ec2_server")

    # substacks for volumes
    stack.add_substack('config0-hub:::ebs_volume')
    stack.add_substack('config0-hub:::ebs_modify')

    # Initialize Variables in stack
    stack.init_variables()
    stack.init_substacks()
    stack.init_shelloutconfigs()

    _eval_tags_labels(stack)

    # Determine the ami
    if stack.get_attr("ami_filter") and stack.get_attr("ami_owner"):
        stack.logger.debug("Will determine AMI through filter {} and owner {}".format(stack.ami_filter,
                                                                                      stack.ami_owner))
    elif stack.get_attr("ami"):
        stack.logger.debug("AMI provided as {}".format(stack.ami)),
    else:
        msg = "Cannot determine the AMI for ec2 server creation"
        stack.ehandle.NeedRtInput(message=msg)

    # security groups
    if stack.get_attr("security_group_ids"):
        stack.set_variable("security_group_ids",
                           ",".join(stack.to_list(stack.security_group_ids)),
                           tags="env_var",
                           types="str")
    elif stack.get_attr("security_groups"):
        stack.set_variable("security_groups",
                           ",".join(stack.to_list(stack.security_groups)),
                           tags="env_var",
                           types="str")

    stack.set_variable("resource_type",
                       "server",
                       tags="ec2_server",
                       types="str")

    # Set environment variables for the shellout
    # to create the server
    stack.env_vars = stack.get_tagged_vars(tag="env_var",
                                           uppercase=True,
                                           output="dict")

    stack.env_vars["METHOD"] = "create"
    stack.env_vars["INSERT_IF_EXISTS"] = True
    stack.env_vars["NAME"] = stack.hostname
    stack.env_vars["KEY"] = stack.ssh_key_name

    # ami info
    if stack.get_attr("ami"):
        stack.env_vars["AMI"] = stack.ami
    else:
        stack.env_vars["AMI_FILTER"] = stack.ami_filter
        stack.env_vars["AMI_OWNER"] = stack.ami_owner

    stack.verify_variables()

    inputargs = stack.get_tagged_vars(tag="ec2_server",
                                      output="dict")

    inputargs = {"display": True,
                 "human_description": 'Create an EC2 server hostname "{}"'.format(stack.hostname),
                 "env_vars": json.dumps(stack.env_vars),
                 "automation_phase": "infrastructure",
                 "retries": 2,
                 "timeout": 300,
                 "wait_last_run": 2}

    stack.ec2_server.resource_exec(**inputargs)

    if not stack.get_attr("volume_size"):
        return stack.get_results()

    if not stack.get_attr("volume_name"):
        return stack.get_results()

    ##########################################################
    # OPTIONAL mounting of extra volume
    # extra disk requires minimally
    # volume_name and volume_size
    ##########################################################

    # create volume
    arguments = stack.get_tagged_vars(tag="ebs",
                                      output="dict")

    human_description = "Creates ebs volume {}".format(stack.volume_name)

    inputargs = {"arguments": arguments,
                 "automation_phase":"infrastructure",
                 "human_description": human_description }

    stack.ebs_volume.insert(display=None, 
                            **inputargs)

    return stack.get_results()

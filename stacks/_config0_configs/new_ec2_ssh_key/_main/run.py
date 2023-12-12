def run(stackargs):

    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_optional(key="name")
    stack.parse.add_optional(key="key_name")
    stack.parse.add_optional(key="schedule_id")
    stack.parse.add_optional(key="run_id")
    stack.parse.add_optional(key="job_instance_id")
    stack.parse.add_optional(key="job_id")
    stack.parse.add_optional(key="aws_default_region", default="us-east-1")

    # declare execution groups
    stack.add_substack("config0-hub:::new_ssh_key")
    stack.add_substack("config0-hub:::ec2_ssh_upload")

    # Initialize Variables in stack
    stack.init_variables()
    stack.init_substacks()

    if not stack.get_attr("key_name") and stack.get_attr("name"):
        stack.set_variable("key_name", stack.name)

    if not stack.get_attr("key_name"):
        msg = "key_name or name variable has to be set"
        raise Exception(msg)

    # new ssh key
    arguments = {"key_name": stack.key_name,
                 "run_id": stack.run_id}

    arguments["schedule_id"] = stack.schedule_id
    arguments["job_instance_id"] = stack.job_instance_id
    arguments["job_id"] = stack.job_id

    inputargs = {"arguments": arguments}
    inputargs["automation_phase"] = "infrastructure"

    human_description = 'create ssh key name {}'.format(stack.key_name)
    inputargs["human_description"] = human_description

    stack.new_ssh_key.insert(display=True, **inputargs)

    # upload ssh key
    arguments = {"key_name": stack.key_name}
    arguments["schedule_id"] = stack.schedule_id
    arguments["run_id"] = stack.run_id
    arguments["job_instance_id"] = stack.job_instance_id
    arguments["job_id"] = stack.job_id
    arguments["aws_default_region"] = stack.aws_default_region

    inputargs = {"arguments": arguments}
    inputargs["automation_phase"] = "infrastructure"

    human_description = 'upload ssh_public_key {} to EC2'.format(
        stack.key_name)
    inputargs["human_description"] = human_description

    stack.ec2_ssh_upload.insert(display=True, **inputargs)

    return stack.get_results()

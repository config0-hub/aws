"""
Copyright (C) 2025 Gary Leong gary@config0.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from config0_publisher.terraform import TFConstructor


def run(stackargs):
    import random

    # instantiate authoring stack
    stack = newStack(stackargs)

    stack.parse.add_optional(key="subnet_ids",  # comma delimited
                             types="str")

    stack.parse.add_required(key="hostname",
                             tags="tfvar,db,ebs",
                             default="_random",
                             types="str")

    stack.parse.add_required(key="ssh_key_name",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="ami_filter",
                             default='ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*',
                             tags="tfvar",
                             types="str")

    # default is canonical
    stack.parse.add_optional(key="ami_owner",
                             default='099720109477',
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="instance_type",
                             default="t3.micro",
                             tags="tfvar,db",
                             types="str")

    # we need to use string value for true b/c tfvar
    stack.parse.add_optional(key="associate_public_ip_address",
                             default="true",
                             tags="tfvar",
                             types="bool")

    stack.parse.add_optional(key="disktype",
                             default="gp2",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="disksize",
                             default="20",
                             tags="tfvar",
                             types="int")

    # this should be b64 encoded
    stack.parse.add_optional(key="user_data",
                             default="null",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="iam_instance_profile",
                             tags="tfvar",
                             types="str")

    # SSM executor targeting: the executor install stack promotes an instance
    # profile name and a canonical managed tag; a server consuming them
    # becomes SendCommand-targetable. The default orchestrated_by=config0 tag
    # does NOT satisfy the executor's SendCommand tag condition.
    stack.parse.add_optional(key="instance_profile_name",
                             types="str")

    stack.parse.add_optional(key="managed_tag_key",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="managed_tag_value",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="security_group_ids",  # comma delimited
                             types="str")

    stack.parse.add_optional(key="sg_id",
                             types="str")

    stack.parse.add_optional(key="ami",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="aws_default_region",
                             default="eu-west-1",
                             tags="tfvar,resource,db,tf_exec_env,ebs",
                             types="str")

    # extra disk
    stack.parse.add_optional(key="volume_name",
                             types="str",
                             tags="ebs")

    stack.parse.add_optional(key="volume_size",
                             types="int",
                             tags="ebs")

    stack.parse.add_optional(key="volume_mountpoint",
                             types="str",
                             tags="ebs")

    stack.parse.add_optional(key="volume_fstype",
                             types="str",
                             tags="ebs")

    # the config network to configure the volume
    stack.parse.add_optional(key="config_network",
                             choices=["private", "public"],
                             types="str",
                             tags="ebs",
                             default="private")

    # substacks for volumes
    stack.add_substack('config0-hub:::aws_storage::ebs_volume')

    # tf_execgroup alias isn't necessary, but it
    # provides some standardization across tf stacks
    stack.add_execgroup("config0-hub:::aws::ec2_server", "tf_execgroup")

    # add substack
    stack.add_substack('config0-hub:::config0_core::tf_executor')

    # initialize
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    # random element for subnet_id
    if stack.get_attr("subnet_ids"):
        avail_subnets = stack.to_list(stack.subnet_ids)
        subnet_element = random.randrange(len(avail_subnets) - 1)
        stack.set_variable("subnet_id",
                           avail_subnets[subnet_element],
                           tags="tfvar,db",
                           types="str")

    # security group id
    if stack.get_attr("security_group_ids"):
        stack.parse.tag_key(key="security_group_ids",
                            tags="tfvar,db")
    elif stack.get_attr("sg_id"):
        stack.set_variable("security_group_ids",
                           stack.sg_id,
                           tags="tfvar,db",
                           types="str")

    # executor instance profile: instance_profile_name is the executor-facing
    # input; it feeds the same terraform var as iam_instance_profile.
    # Supplying both is ambiguous - fail loud.
    if stack.get_attr("instance_profile_name") and stack.get_attr("iam_instance_profile"):
        raise ValueError("supply instance_profile_name or iam_instance_profile, not both")

    if stack.get_attr("instance_profile_name"):
        stack.set_variable("iam_instance_profile",
                           stack.instance_profile_name,
                           tags="tfvar",
                           types="str")

    # the managed tag only targets an instance when key AND value are applied
    if bool(stack.get_attr("managed_tag_key")) != bool(stack.get_attr("managed_tag_value")):
        raise ValueError("managed_tag_key and managed_tag_value must be supplied together")

    stack.set_variable("timeout", 600)

    # use the terraform constructor (helper)
    tf = TFConstructor(stack=stack,
                       execgroup_name=stack.tf_execgroup.name,
                       provider="aws",
                       resource_name=stack.hostname,
                       resource_type="server")

    tf.include(values={
        "aws_default_region": stack.aws_default_region,
        "hostname": stack.hostname
    })

    # SSM target identity facts on the server record: the host-order seam
    # resolves ONE server row and validates account/region/instance-id/
    # profile/managed tag from it - never an untrusted payload id.
    tf.include(keys=["account_id",
                     "region",
                     "instance_id",
                     "instance_profile",
                     "managed_tag_key",
                     "managed_tag_value"])

    # resource output to show on saas ui
    tf.output(keys=["id", "private_ip", "public_ip"])

    # finalize the tf_executor
    stack.tf_executor.insert(display=True,
                             **tf.get())

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

    human_description = f"Creates ebs volume {stack.volume_name}"

    inputargs = {"arguments": arguments,
                 "automation_phase": "infrastructure",
                 "human_description": human_description}

    stack.ebs_volume.insert(display=None,
                            **inputargs)

    return stack.get_results()

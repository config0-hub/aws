"""
# Copyright (C) 2025 Gary Leong <gary@config0.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from config0_publisher.terraform import TFConstructor


def run(stackargs):

    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_required(key="subnet_ids")

    stack.parse.add_required(key="sg_id",
                             types="str")

    # the cluster name; ecs_access takes it as ecs_cluster
    stack.parse.add_required(key="ecs_cluster",
                             tags="resource,tf_exec_env,db,tfvar",
                             types="str")

    # the service name; ecs_access takes it as ecs_service
    stack.parse.add_optional(key="ecs_service",
                             default=None,
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="cpu",
                             default=256,
                             tags="tfvar",
                             types="int")

    stack.parse.add_optional(key="memory",
                             default=512,
                             tags="tfvar",
                             types="int")

    stack.parse.add_optional(key="desired_count",
                             default=1,
                             tags="tfvar",
                             types="int")

    stack.parse.add_optional(key="aws_default_region",
                             default="eu-west-1",
                             tags="tfvar,db,resource,tf_exec_env",
                             types="str")

    # add execgroup
    stack.add_execgroup("config0-hub:::aws::ecs_service",
                        "tf_execgroup")

    # add substack
    stack.add_substack("config0-hub:::config0_core::tf_executor")

    # initialize
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    stack.set_variable("security_group_ids",
                       stack.to_list(stack.sg_id),
                       tags="tfvar",
                       types="list")

    stack.set_variable("subnet_ids",
                       stack.to_list(stack.subnet_ids),
                       tags="tfvar",
                       types="list")

    # the service defaults to the cluster's name
    if not stack.get_attr("ecs_service"):
        stack.set_variable("ecs_service",
                           stack.ecs_cluster,
                           tags="tfvar,db",
                           types="str")

    stack.set_variable("timeout", 1800)

    # use the terraform constructor (helper)
    tf = TFConstructor(stack=stack,
                       execgroup_name=stack.tf_execgroup.name,
                       provider="aws",
                       resource_name=stack.ecs_cluster,
                       resource_type="ecs")

    tf.include(maps={"id": "arn"})

    output_keys = [
        "ecs_cluster",
        "ecs_service",
        "arn",
        "cluster_arn",
        "task_definition_arn",
        "task_role_arn",
        "log_group_name",
        "launch_type",
        "desired_count",
        "enable_execute_command"
    ]

    tf.output(keys=output_keys)

    # finalize the tf_executor
    stack.tf_executor.insert(display=True, **tf.get())

    return stack.get_results()

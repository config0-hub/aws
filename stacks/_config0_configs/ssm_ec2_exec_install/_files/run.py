"""
Copyright (C) 2025 Gary Leong <gary@config0.com>

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

    # instantiate authoring stack
    stack = newStack(stackargs)

    # aws_region matches the vendored terraform's variable.aws_region
    stack.parse.add_optional(key="aws_region",
                             default="ap-northeast-1",
                             tags="tfvar",
                             types="str")

    # declare execution group: the vendored ssm_ec2_exec terraform, applied
    # through the platform's standard terraform resource_wrapper action
    stack.add_execgroup("config0-hub:::aws::ssm_ec2_exec_install",
                        "tf_execgroup")

    # add substack
    stack.add_substack('config0-hub:::config0_core::tf_executor')

    # initialize
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    # use the terraform constructor (helper)
    tf = TFConstructor(stack=stack,
                       execgroup_name=stack.tf_execgroup.name,
                       provider="aws",
                       resource_name="ssm_ec2_exec",
                       resource_type="ssm_ec2_exec_install")

    tf.include(values={"aws_region": stack.aws_region})

    # resource output to show on saas ui
    tf.output(keys=["state_machine_arn", "bucket_name", "instance_profile_name"])

    # finalize the tf_executor
    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()

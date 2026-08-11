"""
Copyright (C) 2026 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from config0_publisher.terraform import TFConstructor


def run(stackargs):
    stack = newStack(stackargs)

    stack.parse.add_required(key="key_name",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="aws_default_region",
                             default="ap-northeast-1",
                             tags="tfvar,db,resource,tf_exec_env",
                             types="str")

    stack.add_execgroup("config0-hub:::aws::ec2_keypair",
                        "tf_execgroup")
    stack.add_substack("config0-hub:::config0_core::tf_executor")

    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    tf = TFConstructor(stack=stack,
                       provider="aws",
                       execgroup_name=stack.tf_execgroup.name,
                       resource_name=stack.key_name,
                       resource_type="ssh_key_pair")

    tf.include(keys=["key_name", "key_pair_id", "fingerprint"])

    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()

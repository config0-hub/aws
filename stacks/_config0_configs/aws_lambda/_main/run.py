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

from config0_publisher.terraform import TFConstructor


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
                             default="python3.11",
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
                             tags="tfvar,resource,db,tf_exec_env",
                             types="str")

    # Add execgroup
    stack.add_execgroup("config0-publish:::aws::add_lambda",
                        "tf_execgroup")

    # Add substack
    stack.add_substack('config0-publish:::tf_executor')

    # Initialize Variables in stack
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    if not stack.get_attr("s3_key"):
        stack.set_variable("s3_key",
                           f"{stack.lambda_name}.zip",
                           tags="tfvar",
                           types="str")

    if stack.get_attr("lambda_env_vars_hash"):
        lambda_env_vars = stack.b64_decode(stack.lambda_env_vars_hash)
    else:
        lambda_env_vars = {}

    # It should not take longer than 10 minutes to establish the lambda function
    stack.set_variable("timeout", 600)

    stack.set_variable("lambda_env_vars",
                       lambda_env_vars,
                       tags="tfvar",
                       types="str,dict")

    tf = TFConstructor(stack=stack,
                       provider="aws",
                       execgroup_name=stack.tf_execgroup.name,
                       resource_name=stack.lambda_name,
                       resource_type="aws_lambda")

    tf.include(values={
        "aws_default_region": stack.aws_default_region,
        "function_name": stack.lambda_name
    })

    tf.include(maps={"id": "arn"})

    tf.output(keys=["s3_key",
                   "s3_bucket",
                   "memory_size",
                   "runtime",
                   "handler",
                   "layers",
                   "arn"])

    # finalize the tf_executor
    stack.tf_executor.insert(display=True,
                            **tf.get())

    return stack.get_results()

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


def _get_default_policy(stack):

    actions = [
        "s3:*",
        "lambda:*",
        "ecr:*",
        "ec2:*",
        "ssm:*",
        "eks:*",
        "rds:*"
    ]

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": actions,
                "Effect": "Allow",
                "Resource": "*"
            }
        ]
    }

    if stack.get_attr("allows_hash") or stack.get_attr("denies_hash"):
        policy["Statement"] = []

    if stack.get_attr("denies_hash"):
        denies = stack.b64_decode(stack.denies_hash)

        for _deny in denies:
            _statement = {
                "Action": _deny["actions"],
                "Effect": "Allow",
                "Resource": _deny["resources"]
            }

            policy["Statement"].append(_statement)

    if stack.get_attr("allows_hash"):
        allows = stack.b64_decode(stack.allows_hash)

        for _allow in allows:
            _statement = {
                "Action": _allow["actions"],
                "Effect": "Allow",
                "Resource": _allow["resources"]
            }

            policy["Statement"].append(_statement)

    return policy


def run(stackargs):

    # instantiate authoring stack
    stack = newStack(stackargs)

    stack.parse.add_required(key="iam_name",
                             tags="resource,db,tf_exec_env,tfvar",
                             types="str")

    stack.parse.add_required(key="policy_name",
                             tags="resource,db,tf_exec_env,tfvar",
                             types="str")

    stack.parse.add_optional(key="aws_default_region",
                             default="eu-west-1",
                             tags="tfvar,db,resource,tf_exec_env",
                             types="str")

    # if policy_hash is set, we ignore allows_hash and denies_hash
    stack.parse.add_optional(key="policy_hash")
    stack.parse.add_optional(key="allows_hash")
    stack.parse.add_optional(key="denies_hash")

    stack.add_execgroup("config0-publish:::aws::iam-keys",
                        "tf_execgroup")

    # Add substack
    stack.add_substack('config0-publish:::tf_executor')

    # Initialize
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    if stack.get_attr("policy_hash"):
        policy = stack.b64_decode(str(stack.policy_hash).strip())
    else:
        policy = _get_default_policy(stack)

    stack.set_variable("policy", 
                       stack.b64_encode(policy), 
                       tags="tfvar", 
                       types="str")

    stack.set_variable("timeout", 600)

    stack.verify_variables()

    # use the terraform constructor
    tf = TFConstructor(stack=stack,
                       provider="aws",
                       execgroup_name=stack.tf_execgroup.name,
                       resource_name=stack.policy_name,
                       resource_type="credentials")

    tf.include(values={"cred_type": "aws"})

    tf.include(maps={
        "values": {
            "AWS_ACCESS_KEY_ID": "id",
            "AWS_SECRET_ACCESS_KEY": "secret"
        }
    })

    tf.exclude(keys=["ses_smtp_password_v4"])

    # finalize the tf_executor
    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()
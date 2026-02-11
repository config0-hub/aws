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


def run(stackargs):

    # Instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_optional(key="name")
    stack.parse.add_optional(key="key_name")
    stack.parse.add_optional(key="schedule_id")
    stack.parse.add_optional(key="run_id")
    stack.parse.add_optional(key="job_instance_id")
    stack.parse.add_optional(key="job_id")
    stack.parse.add_optional(key="aws_default_region", default="us-east-1")

    # Declare execution groups
    stack.add_substack("config0-publish:::new_ssh_key")
    stack.add_substack("config0-publish:::ec2_ssh_upload")

    # Initialize Variables in stack
    stack.init_variables()
    stack.init_substacks()

    if not stack.get_attr("key_name") and stack.get_attr("name"):
        stack.set_variable("key_name", stack.name)

    if not stack.get_attr("key_name"):
        msg = "key_name or name variable has to be set"
        raise Exception(msg)

    # New ssh key
    arguments = {
        "key_name": stack.key_name,
        "run_id": stack.run_id,
        "schedule_id": stack.schedule_id,
        "job_instance_id": stack.job_instance_id,
        "job_id": stack.job_id
    }

    inputargs = {
        "arguments": arguments,
        "automation_phase": "infrastructure",
        "human_description": f'Create SSH key name {stack.key_name}'
    }

    stack.new_ssh_key.insert(display=True, **inputargs)

    # Upload ssh key
    arguments = {
        "key_name": stack.key_name,
        "schedule_id": stack.schedule_id,
        "run_id": stack.run_id,
        "job_instance_id": stack.job_instance_id,
        "job_id": stack.job_id,
        "aws_default_region": stack.aws_default_region
    }
                 
    inputargs = {
        "arguments": arguments,
        "automation_phase": "infrastructure",
        "human_description": f'Upload SSH public key {stack.key_name} to EC2'
    }

    stack.ec2_ssh_upload.insert(display=True, **inputargs)

    return stack.get_results()
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

# The admin set's keys are the provider's own environment names, so the env
# file the engine sources before every tofu command needs no renaming.
ADMIN_KEYS = ("TAILSCALE_OAUTH_CLIENT_ID", "TAILSCALE_OAUTH_CLIENT_SECRET")


def _admin_client(stack):
    """The admin OAuth client from stack.inputvars, values decoded.

    Input variable values are entered base64. A missing key fails loud
    naming the key and the set, never a value.
    """
    import base64

    client = {}
    for key in ADMIN_KEYS:
        value = stack.inputvars.get(key)
        if not value:
            raise ValueError(
                f"input variable set {stack.admin_set_name} has no {key}"
            )
        client[key] = base64.b64decode(value, validate=True).decode()
    return client


def run(stackargs):
    """Capture an agent server's Tailscale device (provisional), delete it on destroy.

    agent_server inserts this stack after its server order when Tailscale is
    on. One Terraform order reads the device the server joined with at boot;
    its row is newer than the server row, so a delete a server destroys it
    first, deleting the device through the API with the admin client.
    """

    stack = newStack(stackargs)

    stack.parse.add_required(key="hostname",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="tailscale_tag",
                             default="tag:config0",
                             tags="tfvar",
                             types="str")

    # The input variable set saas-api references on the server's schedule;
    # its keys arrive in stack.inputvars.
    stack.parse.add_optional(key="admin_set_name",
                             default="tailscale_admin",
                             types="str")

    stack.add_execgroup("config0-hub:::aws::tailscale_device",
                        "tf_execgroup")

    stack.add_substack('config0-hub:::config0_core::tf_executor')

    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    tf = TFConstructor(stack=stack,
                       execgroup_name=stack.tf_execgroup.name,
                       provider="tailscale",
                       resource_name=stack.hostname,
                       ssm_obj=_admin_client(stack),
                       resource_type="tailscale_device")

    tf.include(keys=["tailscale_node_id",
                     "tailscale_hostname",
                     "tailscale_tag"])

    tf.output(keys=["tailscale_hostname", "tailscale_node_id"])

    stack.tf_executor.insert(display=True, **tf.get())

    return stack.get_results()

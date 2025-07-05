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


def _get_ssh_public_key(stack):

    _lookup = {
        "must_be_one": True,
        "resource_type": "ssh_key_pair",
        "name": stack.key_name
    }
    
    try:
        results = stack.get_resource(decrypt=True, **_lookup)[0]
    except:
        results = None

    if results:
        stack.logger.debug(f"found public key {_lookup}")
        
    if not results:
        _lookup = {
            "must_be_one": True,
            "resource_type": "ssh_public_key",
            "name": stack.key_name
        }

        try:
            results = stack.get_resource(decrypt=True, **_lookup)[0]
        except:
            results = None

        if results:
            stack.logger.debug(f"found public key {_lookup}")

    if not results:
        # inputvars are more generic so
        # we only take values key field
        _lookup = {
            "must_be_one": True,
            "resource_type": "inputvars",
            "name": stack.key_name,
            "fields": ["values"],
            "flatten": True
        }

        try:
            results = stack.get_resource(decrypt=True, **_lookup)[0]
        except:
            results = None

        if results:
            stack.logger.debug(f"found public key {_lookup}")

    if not results:
        raise Exception("could not retrieve public key")

    public_key_hash = results.get("public_key_hash")
    
    if public_key_hash:
        return public_key_hash

    public_key = results.get("public_key")

    if public_key:
        return stack.b64_encode(public_key)

    raise Exception("could not retrieve public key/public key hash from query")


def run(stackargs):

    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_optional(key="key_name",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="name",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="public_key",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="aws_default_region",
                             default="eu-west-1",
                             tags="tfvar,resource,db,tf_exec_env",
                             types="str")

    # Add execgroup
    stack.add_execgroup("config0-publish:::aws::ssh_key_upload",
                        "tf_execgroup")

    # Add substack
    stack.add_substack('config0-publish:::tf_executor')

    # Initialize Variables in stack
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    if not stack.get_attr("key_name") and stack.get_attr("name"):
        stack.set_variable("key_name",
                           stack.name,
                           tags="tfvar,db",
                           types="str")

    if not stack.get_attr("key_name"):
        msg = "key_name or name variable has to be set"
        raise Exception(msg)

    if not stack.get_attr("public_key") and stack.inputvars.get("public_key"):
        stack.logger.debug_highlight("public key found in inputvars")
        stack.set_variable("public_key",
                           stack.inputvars["public_key"],
                           tags="tfvar",
                           types="str")
    elif not stack.get_attr("public_key"):
        stack.logger.debug_highlight("public key found in resources table")
        _public_key = _get_ssh_public_key(stack)
        stack.set_variable("public_key",
                           _public_key,
                           tags="tfvar",
                           types="str")

    if not stack.get_attr("public_key"):
        msg = "public_key is missing"
        raise Exception(msg)

    # use the terraform constructor
    tf = TFConstructor(stack=stack,
                       provider="aws",
                       execgroup_name=stack.tf_execgroup.name,
                       resource_name=stack.key_name,
                       resource_type="ssh_public_key")

    # finalize the tf_executor
    stack.tf_executor.insert(display=True, **tf.get())

    return stack.get_results()

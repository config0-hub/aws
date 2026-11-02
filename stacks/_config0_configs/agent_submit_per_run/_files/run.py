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

import json

# The submit arguments this composition hands agent_submit unchanged.
SUBMIT_ARGUMENTS = (
    "call_name", "task", "task_schema", "adapter", "model", "key_set_name",
    "repository_url", "branch", "repository_credential_set_name",
    "max_turns", "max_budget_usd", "artifact_prefix", "phase2complete_timeout",
)


# The model key sets each adapter takes, named for the tool's variable: the
# runner daemon's brief refuses any other pair (config0_agent_runner brief.py).
ADAPTER_KEY_SETS = {
    "claude": ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"),
    "pi": ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"),
}


def per_run_hostname(run_id):
    """Per-run server hostname: ai- plus the run id with underscores as hyphens."""
    return f"ai-{run_id.replace('_', '-')}"


def check_call(stack):
    """Refuse at emission what the daemon would refuse after the brief is written.

    The daemon deletes a brief it cannot read and the order then waits out
    its deadline, so a typo fails here, before any order or server exists.
    Returns the parsed task schema.
    """
    task_schema = json.loads(stack.task_schema)
    if not isinstance(task_schema, dict):
        raise ValueError("task_schema must be a JSON object, a JSON Schema")
    if stack.key_set_name not in ADAPTER_KEY_SETS[stack.adapter]:
        raise ValueError(
            f"{stack.adapter} takes the key set {' or '.join(ADAPTER_KEY_SETS[stack.adapter])}, "
            f"not {stack.key_set_name!r}"
        )
    if not stack.repository_url.startswith("https://"):
        raise ValueError(f"repository_url must be an https:// URL: {stack.repository_url!r}")
    if stack.max_turns < 1 or stack.max_budget_usd <= 0:
        raise ValueError("max_turns must be at least 1 and max_budget_usd above 0")
    if not stack.artifact_prefix.startswith("s3://") or len(stack.artifact_prefix) <= len("s3://"):
        raise ValueError(f"artifact_prefix must be s3://<bucket>/<prefix>: {stack.artifact_prefix!r}")
    return task_schema


def run(stackargs):
    """One agent call on a server that lives for this run only (design A1).

    1. agent_server creates the server ai-<run id>, its queue and its role,
       with lifetime per_run and exactly the grants of the submit order below:
       the artifact prefix and the named sets of the model key and the
       repository credential.
    2. agent_submit hands the brief to that server and parks until its result.
    3. Only after the submit order succeeded, delete_resource removes the
       server row's resources, must_exists: the instance, its queue, its
       security group, its profile and its role, one Terraform state. A failed
       or cancelled call removes nothing: the server, its queue and its role
       stay for the user.

    Author warning: the job's archive.timeout (spec: schedule: in
    config0.yaml; 4800 s by default) must cover the server, the park and the
    removal, and fit inside run_timeout.
    """

    stack = newStack(stackargs)

    # The server: where it runs and what it may write.
    stack.parse.add_required(key="subnet_id",
                             types="str")

    stack.parse.add_required(key="aws_default_region",
                             types="str")

    stack.parse.add_optional(key="instance_type",
                             types="str")

    # The call, as agent_submit takes it.
    stack.parse.add_required(key="call_name",
                             types="str")

    stack.parse.add_required(key="task",
                             types="str")

    stack.parse.add_required(key="task_schema",
                             types="str")

    stack.parse.add_optional(key="adapter",
                             default="claude",
                             choices=["claude", "pi"],
                             types="str")

    stack.parse.add_optional(key="model",
                             types="str")

    stack.parse.add_required(key="key_set_name",
                             types="str")

    stack.parse.add_required(key="repository_url",
                             types="str")

    # Empty, the daemon clones the repository's default branch.
    stack.parse.add_optional(key="branch",
                             default="",
                             types="str")

    stack.parse.add_optional(key="repository_credential_set_name",
                             types="str")

    stack.parse.add_required(key="max_turns",
                             types="int")

    stack.parse.add_required(key="max_budget_usd",
                             types="float")

    stack.parse.add_required(key="artifact_prefix",
                             types="str")

    # P, short enough by default that the server, the park and the removal
    # fit the default 4800 s job.
    stack.parse.add_optional(key="phase2complete_timeout",
                             default=1800,
                             types="int")

    stack.parse.add_optional(key="run_timeout",
                             default=7200,
                             types="int")

    stack.add_substack("config0-hub:::aws::agent_server")
    stack.add_substack("config0-hub:::aws::agent_submit")
    stack.add_substack("config0-hub:::config0_core::delete_resource")

    stack.init_variables()
    stack.init_substacks()

    # The call's own checks, before the server exists (agent_submit repeats them).
    check_call(stack)

    hostname = per_run_hostname(stack.run_id)
    # agent_server names the instance role agent-server-<hostname>, and IAM caps
    # a role name at 64 characters: refused here, before the server, not in Terraform.
    role_name = f"agent-server-{hostname}"
    if len(role_name) > 64:
        raise ValueError(f"the per-run server's role name {role_name} is {len(role_name)} characters; "
                         "IAM allows at most 64, so the run id may be at most 48")

    # The exact named reads of the submit order, nothing wider.
    key_set_names = [stack.key_set_name]
    if stack.get_attr("repository_credential_set_name"):
        key_set_names.append(stack.repository_credential_set_name)

    server_arguments = {
        # agent_server is a Class Helper: run its server job alone, as
        # saas-api's per-job expansion would, never its notifiers.
        "jobs": ["server"],
        "hostname": hostname,
        "subnet_id": stack.subnet_id,
        "aws_default_region": stack.aws_default_region,
        "artifact_prefix": stack.artifact_prefix,
        "key_set_names": ",".join(key_set_names),
        "lifetime": "per_run",
    }
    if stack.get_attr("instance_type"):
        server_arguments["instance_type"] = stack.instance_type

    stack.agent_server.insert(display=True,
                              arguments=server_arguments,
                              human_description=f"Create the per-run agent server {hostname}")

    # The submit order needs the server row, written when its order finalizes.
    stack.wait_all()

    submit_arguments = {key: stack.get_attr(key) for key in SUBMIT_ARGUMENTS
                        if stack.get_attr(key) is not None}
    submit_arguments["hostname"] = hostname

    stack.agent_submit.insert(display=True,
                              arguments=submit_arguments,
                              human_description=f'Submit "{stack.call_name}" to {hostname}')

    # Removal follows only a settled submit order; a failed one fails the job,
    # so the removal never runs and the server stays.
    stack.wait_all()

    stack.delete_resource.insert(display=True,
                                 arguments={"resource_type": "server",
                                            "hostname": hostname,
                                            "must_exists": "true"},
                                 human_description=f"Remove the per-run agent server {hostname}")

    return stack.get_results()

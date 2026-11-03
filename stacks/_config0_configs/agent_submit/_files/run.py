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

# Every value the submit order's fire pass reads from its inputted values
# (config0_cli handlers/agent_submit.py), copied from the stack arguments.
SUBMIT_KEYS = (
    "call_name", "task", "adapter", "model", "key_set_name",
    "repository_url", "branch", "repository_credential_set_name",
    "max_turns", "max_budget_usd", "hostname", "server_id",
    "artifact_prefix", "phase2complete_timeout",
)


# The model key sets each adapter takes, named for the tool's variable: the
# runner daemon's brief refuses any other pair (config0_agent_runner brief.py).
ADAPTER_KEY_SETS = {
    "claude": ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"),
    "pi": ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"),
}


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
    """Emit one submit order: one brief to one agent server, then park until its result.

    The order has the role agent/server/submit and runs two passes. The fire
    pass resolves the server, fixes the deadline at now plus
    phase2complete_timeout, writes the brief and sends one message to the
    server's queue. The finalize pass records one agent_result row named
    call_name, carrying run_id and the labels. The row is global: a later
    order, a later project or a later run reads it with a selector::: whose
    match sets filter.resource_type agent_result and the labels or keys.name
    the call name, and adds run_id when it must be this run's row.

    Author warning: the job's archive.timeout, phase2complete_timeout and
    every later order must fit inside run_timeout; a longer value is the
    author's mistake.
    """

    stack = newStack(stackargs)

    # The row's name: once per run. A second submit order with the same call
    # name in one run fails at its finalize pass.
    stack.parse.add_required(key="call_name",
                             types="str")

    # The task text and the JSON Schema its result must match.
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

    # The model key's input variable set, named for the tool's variable
    # (ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN or OPENAI_API_KEY). The
    # server must have been granted it by name.
    stack.parse.add_required(key="key_set_name",
                             types="str")

    # What the daemon clones: the branch head at clone time, never a commit.
    stack.parse.add_required(key="repository_url",
                             types="str")

    # Empty, the brief carries it empty and the daemon clones the
    # repository's default branch.
    stack.parse.add_optional(key="branch",
                             default="",
                             types="str")

    # The read credential's input variable set, for a private repository.
    stack.parse.add_optional(key="repository_credential_set_name",
                             types="str")

    # Bounds: turns per agent process and the measured-spend cap of the order.
    stack.parse.add_required(key="max_turns",
                             types="int")

    stack.parse.add_required(key="max_budget_usd",
                             types="float")

    # The server, named one way: its hostname, its labels as a JSON object,
    # or its row id. A selector::: in config0.yaml can fill hostname or
    # server_id. An instance id is never an argument.
    stack.parse.add_optional(key="hostname",
                             types="str")

    stack.parse.add_optional(key="server_labels",
                             types="str")

    stack.parse.add_optional(key="server_id",
                             types="str")

    # The result row's labels, a JSON object of label names to values: a
    # reader matches the agent_result row by them.
    stack.parse.add_optional(key="labels",
                             types="str")

    # The customer's s3:// prefix the order's brief and artifacts go under,
    # inside the server's artifact_prefix grant.
    stack.parse.add_required(key="artifact_prefix",
                             types="str")

    # P, the park: the work deadline is the fire pass plus P. The fire pass
    # itself keeps the order's short timeout of 900 s.
    stack.parse.add_optional(key="phase2complete_timeout",
                             default=3600,
                             types="int")

    # The run clock of an ai project that runs this stack (at most 86400 s).
    stack.parse.add_optional(key="run_timeout",
                             default=7200,
                             types="int")

    stack.init_variables()

    named = [key for key in ("hostname", "server_labels", "server_id") if stack.get_attr(key)]
    if len(named) != 1:
        raise ValueError(f"name the server one way: hostname, server_labels or server_id; got {named}")

    task_schema = check_call(stack)

    overide_values = {key: stack.get_attr(key) for key in SUBMIT_KEYS if stack.get_attr(key) is not None}
    overide_values["task_schema"] = task_schema
    if stack.get_attr("server_labels"):
        server_labels = json.loads(stack.server_labels)
        if not isinstance(server_labels, dict):
            raise ValueError("server_labels must be a JSON object of label names to values")
        overide_values["server_labels"] = server_labels
    if stack.get_attr("labels"):
        labels = json.loads(stack.labels)
        if not isinstance(labels, dict):
            raise ValueError("labels must be a JSON object of label names to values")
        overide_values["labels"] = labels

    stack.add_jiffy_cli(order_type="agent-server-submit::api",
                        role="agent/server/submit",
                        pargs="agent server submit",
                        overide_values=overide_values,
                        timeout=900,
                        retries=1,
                        display=True,
                        human_description=f'Submit "{stack.call_name}" to an agent server')

    return stack.get_results()

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
# No task: the fire pass runs the attempt group row's current brief.
SUBMIT_KEYS = (
    "call", "call_name", "adapter", "model", "key_set_name",
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
    its deadline, so a typo fails here, before any order exists.
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
    """Layer 1, the agent call (provisional, design J): one attempt's submit order, then its evaluation.

    The body runs when this stack's exec order fires, at the attempt's turn.
    It reads the attempt_groups row and fails loud unless the row is at this
    attempt. It emits the submit order with no task text, so the submit
    order's fire pass runs the row's current brief: brief 1, or brief n
    that the previous evaluation order wrote. Then it inserts
    agent_evaluate, whose order decides the attempt.

    Every row carries attempt_group_id and attempt: the submit order, the
    agent_evaluate insert and exec rows, and the evaluation order.
    """

    stack = newStack(stackargs)

    # The attempt_groups row's _id and this attempt's number.
    stack.parse.add_required(key="attempt_group_id",
                             types="str")

    stack.parse.add_required(key="attempt",
                             types="int")

    # Which attempts[n] sub-entry the two orders write. Phase 5 has the
    # work call only; review is phase 6's.
    stack.parse.add_required(key="call",
                             choices=["work"],
                             types="str")

    # The agent_result row's name: unique in the run, so one per attempt.
    stack.parse.add_required(key="call_name",
                             types="str")

    # The JSON Schema the task result must match.
    stack.parse.add_required(key="task_schema",
                             types="str")

    # The author's rules over the task result, a JSON Schema as a JSON
    # string, checked by the evaluation order (provisional).
    stack.parse.add_optional(key="acceptance_schema",
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

    # The server, named one way, as agent_submit takes it.
    stack.parse.add_optional(key="hostname",
                             types="str")

    stack.parse.add_optional(key="server_labels",
                             types="str")

    stack.parse.add_optional(key="server_id",
                             types="str")

    stack.parse.add_required(key="artifact_prefix",
                             types="str")

    # P, the park: the work deadline is the fire pass plus P.
    stack.parse.add_optional(key="phase2complete_timeout",
                             default=1200,
                             types="int")

    stack.add_substack("config0-hub:::aws::agent_evaluate")

    stack.init_variables()
    stack.init_substacks()

    named = [key for key in ("hostname", "server_labels", "server_id") if stack.get_attr(key)]
    if len(named) != 1:
        raise ValueError(f"name the server one way: hostname, server_labels or server_id; got {named}")

    task_schema = check_call(stack)

    # The row is at this attempt: the previous attempt's evaluation order
    # moved it here, or this is attempt 1.
    group = stack.get_resource(match={"_id": stack.attempt_group_id},
                               must_be_one=True,
                               overlay_tfstate=False)[0]
    if group.get("status") not in ("queued", "in_progress") or group.get("attempt") != stack.attempt:
        raise ValueError(
            f"attempt group {stack.attempt_group_id} reads status={group.get('status')!r} "
            f"attempt={group.get('attempt')!r}; attempt {stack.attempt}'s agent call runs only "
            "while the group is queued or in_progress at its attempt"
        )

    overide_values = {key: stack.get_attr(key) for key in SUBMIT_KEYS if stack.get_attr(key) is not None}
    overide_values["task_schema"] = task_schema
    if stack.get_attr("server_labels"):
        server_labels = json.loads(stack.server_labels)
        if not isinstance(server_labels, dict):
            raise ValueError("server_labels must be a JSON object of label names to values")
        overide_values["server_labels"] = server_labels

    stack.add_jiffy_cli(order_type="agent-server-submit::api",
                        role="agent/server/submit",
                        pargs="agent server submit",
                        overide_values=overide_values,
                        timeout=900,
                        retries=1,
                        attempt_group_id=stack.attempt_group_id,
                        attempt=stack.attempt,
                        display=True,
                        human_description=f'Submit "{stack.call_name}", attempt {stack.attempt}')

    evaluate_arguments = {
        "attempt_group_id": stack.attempt_group_id,
        "attempt": stack.attempt,
        "call": stack.call,
        # A Python string: a bare YAML yes would arrive as a boolean.
        "writes_evaluated": "yes",
    }
    if stack.get_attr("acceptance_schema"):
        evaluate_arguments["acceptance_schema"] = stack.acceptance_schema

    stack.agent_evaluate.insert(display=True,
                                arguments=evaluate_arguments,
                                human_description=f"Evaluate attempt {stack.attempt}")

    return stack.get_results()

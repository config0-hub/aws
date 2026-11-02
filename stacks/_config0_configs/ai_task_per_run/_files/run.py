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

# The arguments this composition hands ai_task unchanged.
TASK_ARGUMENTS = (
    "task_name", "task", "max_attempts", "result_selector",
    "task_schema", "acceptance_schema", "adapter", "model", "key_set_name",
    "repository_url", "branch", "repository_credential_set_name",
    "max_turns", "max_budget_usd", "artifact_prefix", "phase2complete_timeout",
    "review_adapter", "review_model", "review_key_set_name", "review_task_schema",
    "threshold", "interactive", "answer_wait_seconds",
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


# What a review call's task result must carry (design J2).
REVIEW_RESULT_KEYS = ("score", "findings")


def check_calls(stack):
    """Refuse at emission what the daemon or a later body would refuse, before the server exists."""
    task_schema = json.loads(stack.task_schema)
    if not isinstance(task_schema, dict):
        raise ValueError("task_schema must be a JSON object, a JSON Schema")
    calls = [(stack.adapter, stack.key_set_name)]
    if stack.get_attr("review_key_set_name"):
        calls.append((stack.review_adapter, stack.review_key_set_name))
        if stack.get_attr("review_task_schema"):
            review_schema = json.loads(stack.review_task_schema)
            missing = [key for key in REVIEW_RESULT_KEYS
                       if not isinstance(review_schema, dict) or key not in review_schema.get("required", [])]
            if missing:
                raise ValueError(f"review_task_schema must require {list(REVIEW_RESULT_KEYS)}; missing {missing}")
    for adapter, key_set_name in calls:
        if key_set_name not in ADAPTER_KEY_SETS[adapter]:
            raise ValueError(
                f"{adapter} takes the key set {' or '.join(ADAPTER_KEY_SETS[adapter])}, not {key_set_name!r}"
            )
    if not stack.repository_url.startswith("https://"):
        raise ValueError(f"repository_url must be an https:// URL: {stack.repository_url!r}")
    if stack.max_turns < 1 or stack.max_budget_usd <= 0:
        raise ValueError("max_turns must be at least 1 and max_budget_usd above 0")
    if not stack.artifact_prefix.startswith("s3://") or len(stack.artifact_prefix) <= len("s3://"):
        raise ValueError(f"artifact_prefix must be s3://<bucket>/<prefix>: {stack.artifact_prefix!r}")
    if not 0 <= stack.threshold <= 10:
        raise ValueError(f"threshold must be a score from 0 to 10, got {stack.threshold}")
    if stack.answer_wait_seconds <= 0:
        raise ValueError(f"answer_wait_seconds must be positive, got {stack.answer_wait_seconds}")


def run(stackargs):
    """One AI task (layer 3, ai_task) on a server that lives for this run only (provisional).

    1. agent_server creates the server ai-<run id>, its queue and its role,
       with lifetime per_run and exactly the grants of the submit orders: the
       artifact prefix and the named sets of the work's model key, the
       review's model key and the repository credential.
    2. A wait: the submit orders need the server row, written when its order
       finalizes.
    3. ai_task runs the task's attempts on that server: its attempt_groups
       row, one attempt_with_review insert per attempt (work, review, ask),
       then the next deterministic order.
    4. A wait over the task's subtree, then delete_resource removes the
       server row's resources, must_exists. A task whose attempts all failed,
       or whose ask timed out, fails the job, so the removal never runs and
       the server, its queue and its role stay for the user.

    Author warning: answer_wait_seconds defaults to 8 h. For each attempt,
    the work's and the review's phase2complete_timeout, two evaluation
    passes of at most 600 s, answer_wait_seconds when interactive is yes,
    and the ask order's two passes; max_attempts times that, plus the server,
    the next order and the removal, must fit inside the job's
    archive.timeout (spec: schedule: in config0.yaml; 4800 s by default)
    and run_timeout (at most 86400 s). No clock is ever extended; a longer
    value is the author's mistake.
    """

    stack = newStack(stackargs)

    # The server: where it runs and what it may write.
    stack.parse.add_required(key="subnet_id",
                             types="str")

    # On: a public address and no NAT egress check, as agent_server takes it.
    stack.parse.add_optional(key="public_subnet",
                             default="false",
                             types="bool")

    stack.parse.add_required(key="aws_default_region",
                             types="str")

    stack.parse.add_optional(key="instance_type",
                             types="str")

    # The task, as ai_task takes it: the attempt_groups row's name, brief 1
    # and the name of the config0.yaml selector on the row.
    stack.parse.add_required(key="task_name",
                             types="str")

    stack.parse.add_required(key="task",
                             types="str")

    stack.parse.add_optional(key="max_attempts",
                             default=3,
                             types="int")

    stack.parse.add_required(key="result_selector",
                             types="str")

    # The work call.
    stack.parse.add_required(key="task_schema",
                             types="str")

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

    stack.parse.add_required(key="artifact_prefix",
                             types="str")

    stack.parse.add_optional(key="phase2complete_timeout",
                             default=1200,
                             types="int")

    # The review call: the reviewing model and its own key. Unset key: no review.
    stack.parse.add_optional(key="review_adapter",
                             default="claude",
                             choices=["claude", "pi"],
                             types="str")

    stack.parse.add_optional(key="review_model",
                             types="str")

    stack.parse.add_optional(key="review_key_set_name",
                             types="str")

    # Unset: attempt_with_review's schema, an integer score 0 to 10 and findings.
    stack.parse.add_optional(key="review_task_schema",
                             types="str")

    # The score at or above which an attempt succeeds with no person.
    stack.parse.add_optional(key="threshold",
                             default=7,
                             types="int")

    # yes: an attempt below the threshold, or failed with attempts left,
    # waits for a person's answer. A string: a bare YAML yes is a boolean.
    stack.parse.add_optional(key="interactive",
                             default="no",
                             choices=["yes", "no"],
                             types="str")

    # How long the ask order waits for the person: 8 h (decided 2026-10-25).
    stack.parse.add_optional(key="answer_wait_seconds",
                             default=28800,
                             types="int")

    # The run clock of an ai project that runs this stack, at most 86400 s.
    # The default is the cap: the 8 h answer wait alone exceeds a smaller one.
    stack.parse.add_optional(key="run_timeout",
                             default=86400,
                             types="int")

    stack.add_substack("config0-hub:::aws::agent_server")
    stack.add_substack("config0-hub:::aws::ai_task")
    stack.add_substack("config0-hub:::config0_core::delete_resource")

    stack.init_variables()
    stack.init_substacks()

    # ai_task's own checks, before the server exists (ai_task repeats them).
    check_calls(stack)

    hostname = per_run_hostname(stack.run_id)
    # agent_server names the instance role agent-server-<hostname>, and IAM caps
    # a role name at 64 characters: refused here, before the server, not in Terraform.
    role_name = f"agent-server-{hostname}"
    if len(role_name) > 64:
        raise ValueError(f"the per-run server's role name {role_name} is {len(role_name)} characters; "
                         "IAM allows at most 64, so the run id may be at most 48")

    # The exact named reads of the work and review submit orders, nothing wider.
    key_set_names = [stack.key_set_name]
    for key in ("repository_credential_set_name", "review_key_set_name"):
        if stack.get_attr(key):
            key_set_names.append(stack.get_attr(key))

    server_arguments = {
        # agent_server is a Class Helper: run its server job alone, as
        # saas-api's per-job expansion would, never its notifiers.
        "jobs": ["server"],
        "hostname": hostname,
        "subnet_id": stack.subnet_id,
        "public_subnet": stack.public_subnet,
        "aws_default_region": stack.aws_default_region,
        "artifact_prefix": stack.artifact_prefix,
        "key_set_names": ",".join(dict.fromkeys(key_set_names)),
        "lifetime": "per_run",
    }
    if stack.get_attr("instance_type"):
        server_arguments["instance_type"] = stack.instance_type

    stack.agent_server.insert(display=True,
                              arguments=server_arguments,
                              human_description=f"Create the per-run agent server {hostname}")

    # The submit orders need the server row, written when its order finalizes.
    stack.wait_all()

    task_arguments = {key: stack.get_attr(key) for key in TASK_ARGUMENTS
                      if stack.get_attr(key) is not None}
    task_arguments["hostname"] = hostname

    stack.ai_task.insert(display=True,
                         arguments=task_arguments,
                         human_description=f'The AI task "{stack.task_name}" on {hostname}')

    # The removal waits on the task's subtree: every attempt and the next order.
    stack.wait_all()

    stack.delete_resource.insert(display=True,
                                 arguments={"resource_type": "server",
                                            "hostname": hostname,
                                            "must_exists": "true"},
                                 human_description=f"Remove the per-run agent server {hostname}")

    return stack.get_results()

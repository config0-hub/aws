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

# The arguments this composition hands attempt_with_review unchanged.
ATTEMPT_ARGUMENTS = (
    "task_schema", "acceptance_schema", "adapter", "model", "key_set_name",
    "repository_url", "branch", "repository_credential_set_name",
    "max_turns", "max_budget_usd", "hostname", "server_labels", "server_id",
    "artifact_prefix", "phase2complete_timeout",
    "review_adapter", "review_model", "review_key_set_name", "review_task_schema",
    "threshold", "interactive", "answer_wait_seconds",
)


# The model key sets each adapter takes, named for the tool's variable: the
# runner daemon's brief refuses any other pair (config0_agent_runner brief.py).
ADAPTER_KEY_SETS = {
    "claude": ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"),
    "pi": ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"),
}

# What a review call's task result must carry (design J2).
REVIEW_RESULT_KEYS = ("score", "findings")


def check_calls(stack):
    """Refuse at emission what the daemon or a later body would refuse, before the group exists."""
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
    """Layer 3, the AI task (provisional, design J): one task's bounded attempts with review and ask.

    1. Creates the run's attempt_groups row for the task, create-only:
       queued, attempt 1, max_attempts, the task text as brief 1.
    2. Inserts attempt_with_review once per attempt, max_attempts insert
       rows chained by dependency, each with attempt_group_id and its
       attempt. Each body runs at its attempt's turn and its calls read the
       row's current brief then. When an order writes the row evaluated,
       the run publisher cancels the inserts still queued and closes the
       row.
    3. Inserts empty_stack as the next deterministic order, after the last
       attempt insert and its subtree; its description is the selector:::
       on the row named by result_selector, resolved when it fires.

    Rows per attempt: eleven with no review model named, seventeen with
    one, thirteen when failed work makes the review run empty (design J1).

    Author warning: answer_wait_seconds defaults to 8 h. For each attempt,
    the work's and the review's phase2complete_timeout, two evaluation
    passes of at most 600 s, answer_wait_seconds when interactive is yes,
    and the ask order's two passes; max_attempts times that, plus every
    later order, must fit inside the job's archive.timeout and run_timeout
    (at most 86400 s). No clock is ever extended; a longer value is the
    author's mistake.
    """

    stack = newStack(stackargs)

    # The attempt_groups row's name, unique in the run: its _id is an md5
    # over the run id and this name.
    stack.parse.add_required(key="task_name",
                             types="str")

    # Brief 1, the first attempt's task text.
    stack.parse.add_required(key="task",
                             types="str")

    stack.parse.add_optional(key="max_attempts",
                             default=3,
                             types="int")

    # The name of the config0.yaml selector on this task's row.
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

    stack.parse.add_optional(key="hostname",
                             types="str")

    stack.parse.add_optional(key="server_labels",
                             types="str")

    stack.parse.add_optional(key="server_id",
                             types="str")

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

    stack.add_substack("config0-hub:::aws::attempt_with_review")
    stack.add_substack("config0-hub:::config0_core::empty_stack")

    stack.init_variables()
    stack.init_substacks()

    named = [key for key in ("hostname", "server_labels", "server_id") if stack.get_attr(key)]
    if len(named) != 1:
        raise ValueError(f"name the server one way: hostname, server_labels or server_id; got {named}")

    check_calls(stack)

    group = stack.create_attempt_group(task=stack.task_name,
                                       max_attempts=stack.max_attempts,
                                       brief=stack.task)

    attempt_arguments = {key: stack.get_attr(key) for key in ATTEMPT_ARGUMENTS
                         if stack.get_attr(key) is not None}

    for attempt in range(1, stack.max_attempts + 1):
        stack.attempt_with_review.insert(display=True,
                                         arguments={
                                             **attempt_arguments,
                                             "attempt_group_id": group["_id"],
                                             "attempt": attempt,
                                             "task_name": stack.task_name,
                                         },
                                         human_description=f'Attempt {attempt} of "{stack.task_name}"')

    # The next deterministic order: no attempt fields, so the sweep never
    # cancels it; it depends on the last attempt insert and its subtree.
    stack.empty_stack.insert(display=True,
                             arguments={"description": f"selector:::{stack.result_selector}::result_ref"},
                             human_description=f'Read the result of "{stack.task_name}"')

    return stack.get_results()

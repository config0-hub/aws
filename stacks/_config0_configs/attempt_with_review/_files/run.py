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

# The work call arguments this composition hands agent_call unchanged.
CALL_ARGUMENTS = (
    "task_schema", "acceptance_schema", "adapter", "model", "key_set_name",
    "repository_url", "branch", "repository_credential_set_name",
    "max_turns", "max_budget_usd", "hostname", "server_labels", "server_id",
    "artifact_prefix", "phase2complete_timeout",
)

# The arguments the review call shares with the work call: the same
# repository, bounds, server, artifact folder and park.
SHARED_ARGUMENTS = (
    "repository_url", "branch", "repository_credential_set_name",
    "max_turns", "max_budget_usd", "hostname", "server_labels", "server_id",
    "artifact_prefix", "phase2complete_timeout",
)

# The review's task schema when the author names none: the evaluation order
# checks an integer score from 0 to 10 and a list of findings (design J2).
REVIEW_TASK_SCHEMA = {
    "type": "object",
    "required": ["score", "findings"],
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 10},
        "findings": {"type": "array", "items": {"type": "string"}},
    },
}


def run(stackargs):
    """Layer 2, one attempt with review (provisional, design J): work, review, ask.

    The body runs when this stack's exec order fires, at the attempt's turn,
    and inserts three substacks, each behind the previous one and its
    subtree:

    1. agent_call with call work, writes_evaluated no: the work's submit
       order and its evaluation, which records the outcome and exits 0;
    2. agent_call with call review, when review_key_set_name names the
       reviewing model's key: a second model reads the work's diff against
       the brief and returns a score and findings; failed work makes this
       insert run empty;
    3. agent_ask: closes the attempt, composes brief n+1, or parks for the
       person. threshold rides it only when a review is composed.

    With no review model named the attempt is the work call and the ask
    order, three orders of work; with one, five (design J1).
    """

    stack = newStack(stackargs)

    # The attempt_groups row's _id and this attempt's number.
    stack.parse.add_required(key="attempt_group_id",
                             types="str")

    stack.parse.add_required(key="attempt",
                             types="int")

    # The task's name: each call's agent_result row is named after it.
    stack.parse.add_required(key="task_name",
                             types="str")

    # The work call, as agent_call takes it.
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

    # The reviewing model and its own key. Unset key: no review.
    stack.parse.add_optional(key="review_adapter",
                             default="claude",
                             choices=["claude", "pi"],
                             types="str")

    stack.parse.add_optional(key="review_model",
                             types="str")

    stack.parse.add_optional(key="review_key_set_name",
                             types="str")

    # Unset: REVIEW_TASK_SCHEMA, an integer score 0 to 10 and findings.
    stack.parse.add_optional(key="review_task_schema",
                             types="str")

    # The ask order's arguments.
    stack.parse.add_optional(key="threshold",
                             default=7,
                             types="int")

    stack.parse.add_optional(key="interactive",
                             default="no",
                             choices=["yes", "no"],
                             types="str")

    stack.parse.add_optional(key="answer_wait_seconds",
                             default=28800,
                             types="int")

    stack.add_substack("config0-hub:::aws::agent_call")
    stack.add_substack("config0-hub:::aws::agent_ask")

    stack.init_variables()
    stack.init_substacks()

    attempt = {"attempt_group_id": stack.attempt_group_id, "attempt": stack.attempt}

    work = {key: stack.get_attr(key) for key in CALL_ARGUMENTS if stack.get_attr(key) is not None}
    stack.agent_call.insert(display=True,
                            arguments={**work, **attempt,
                                       "call": "work",
                                       # Strings: a bare YAML yes would arrive as a boolean.
                                       "writes_evaluated": "no",
                                       "call_name": f"{stack.task_name}-{stack.attempt}"},
                            human_description=f"Work of attempt {stack.attempt}")

    reviewed = bool(stack.get_attr("review_key_set_name"))
    if reviewed:
        review = {key: stack.get_attr(key) for key in SHARED_ARGUMENTS if stack.get_attr(key) is not None}
        review.update(adapter=stack.review_adapter,
                      key_set_name=stack.review_key_set_name,
                      task_schema=stack.get_attr("review_task_schema") or json.dumps(REVIEW_TASK_SCHEMA))
        if stack.get_attr("review_model"):
            review["model"] = stack.review_model
        stack.agent_call.insert(display=True,
                                arguments={**review, **attempt,
                                           "call": "review",
                                           "writes_evaluated": "no",
                                           "call_name": f"{stack.task_name}-{stack.attempt}-review"},
                                human_description=f"Review of attempt {stack.attempt}")

    ask = {**attempt, "interactive": stack.interactive, "answer_wait_seconds": stack.answer_wait_seconds}
    if reviewed:
        ask["threshold"] = stack.threshold
    stack.agent_ask.insert(display=True,
                           arguments=ask,
                           human_description=f"Decide attempt {stack.attempt}")

    return stack.get_results()

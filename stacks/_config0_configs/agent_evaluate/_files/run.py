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
    """Emit one evaluation order: the deterministic verdict on one attempt (design I5).

    agent_call inserts this stack after its submit order. The order has the
    role agent/evaluate and runs one pass (config0_cli handlers/agent_evaluate.py).
    It reads the attempt_groups row, reads the work's result and event log
    under the attempt's artifact prefix, runs the checks finished, envelope,
    schema, acceptance and diff, and writes the row once: evaluated with
    outcome succeeded; attempt n+1 with brief n+1; or, on the last attempt,
    evaluated with outcome failed, which exits non-zero.

    retries=2 is two passes, one retry (design I7): the retry reads the row
    first, so a write that landed is never repeated.
    """

    stack = newStack(stackargs)

    # The attempt_groups row's _id and this order's attempt number. Both ride
    # the order's top level, so the run publisher's sweep finds the order.
    stack.parse.add_required(key="attempt_group_id",
                             types="str")

    stack.parse.add_required(key="attempt",
                             types="int")

    # Which attempts[n] sub-entry the evaluation reads (design J). Phase 5
    # evaluates the work call only; review is phase 6's.
    stack.parse.add_required(key="call",
                             choices=["work"],
                             types="str")

    # yes: this order is the attempt's last order and writes evaluated.
    # Phase 5 has no ask order, so yes is the only value.
    stack.parse.add_required(key="writes_evaluated",
                             choices=["yes"],
                             types="str")

    # The author's rules over the task result, a JSON Schema as a JSON
    # string (provisional). Unset, the acceptance check passes.
    stack.parse.add_optional(key="acceptance_schema",
                             types="str")

    stack.init_variables()

    overide_values = {
        "call": stack.call,
        "writes_evaluated": stack.writes_evaluated,
    }
    if stack.get_attr("acceptance_schema"):
        overide_values["acceptance_schema"] = stack.acceptance_schema

    stack.add_jiffy_cli(order_type="agent-evaluate::api",
                        role="agent/evaluate",
                        pargs="agent evaluate",
                        overide_values=overide_values,
                        retries=2,
                        attempt_group_id=stack.attempt_group_id,
                        attempt=stack.attempt,
                        display=True,
                        human_description=f"Evaluate attempt {stack.attempt}")

    return stack.get_results()

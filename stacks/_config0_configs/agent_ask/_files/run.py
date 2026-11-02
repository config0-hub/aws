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
    """Emit one ask order: the last order of an attempt in layer 2 (design J2, J3).

    The order has the role agent/ask and two passes (config0_cli
    handlers/agent_ask.py). Its fire pass reads the attempt_groups row:
    work that succeeded with no review, or a score at or above threshold,
    closes the attempt succeeded with no person; otherwise it composes
    brief n+1 by rule from the review's findings or the failed check, or,
    when interactive is yes, parks for the person. The last attempt's
    failed work closes the attempt failed. Its finalize pass applies the
    person's answer: accept, stop, or brief n+1 while another attempt
    remains.

    threshold set means the composition reviews the work; unset, it does
    not. retries=1, one run: no answer by the park's expire_at settles the
    order timed_out with no second park. The park lasts answer_wait_seconds
    from the fire pass; the order's own timeout stays the short pass.

    Author warning: answer_wait_seconds, every submit order's
    phase2complete_timeout, every evaluation pass and the finalize passes
    must fit inside the job's archive.timeout and the stack's run_timeout;
    no clock is ever extended, and a longer value is the author's mistake.
    """

    stack = newStack(stackargs)

    # The attempt_groups row's _id and this order's attempt number. Both ride
    # the order's top level, so the run publisher's sweep finds the order.
    stack.parse.add_required(key="attempt_group_id",
                             types="str")

    stack.parse.add_required(key="attempt",
                             types="int")

    # The score from 0 to 10 at or above which the attempt succeeds with no
    # person. Unset: the composition has no review.
    stack.parse.add_optional(key="threshold",
                             types="int")

    # yes: below the threshold, or failed work with attempts left, parks
    # for the person. A string: a bare YAML yes would arrive as a boolean.
    stack.parse.add_optional(key="interactive",
                             default="no",
                             choices=["yes", "no"],
                             types="str")

    # How long the park waits for the person: 8 h (decided 2026-10-25).
    stack.parse.add_optional(key="answer_wait_seconds",
                             default=28800,
                             types="int")

    stack.init_variables()

    if stack.get_attr("threshold") is not None and not 0 <= stack.threshold <= 10:
        raise ValueError(f"threshold must be a score from 0 to 10, got {stack.threshold}")
    if stack.answer_wait_seconds <= 0:
        raise ValueError(f"answer_wait_seconds must be positive, got {stack.answer_wait_seconds}")

    overide_values = {
        "interactive": stack.interactive,
        "answer_wait_seconds": stack.answer_wait_seconds,
    }
    if stack.get_attr("threshold") is not None:
        overide_values["threshold"] = stack.threshold

    stack.add_jiffy_cli(order_type="agent-ask::api",
                        role="agent/ask",
                        pargs="agent ask",
                        overide_values=overide_values,
                        retries=1,
                        attempt_group_id=stack.attempt_group_id,
                        attempt=stack.attempt,
                        display=True,
                        human_description=f"Decide attempt {stack.attempt}")

    return stack.get_results()

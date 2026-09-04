"""
Copyright (C) 2026 Gary Leong <gary@config0.com>

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


class Main(newSchedStack):
    """Run one day-2 pipeline action (plan phase 6, "Execution, one model").

    One work job plus the gitops status-producer notifiers (the same shape as
    ``gitops_writeback``):

        pipeline_run     `config0 gitops pipeline-run ...` — the CLI verb does
                         everything: reads the `pipeline` / `pipeline_run` /
                         addon records from QHost, binds the commit per the
                         PR-activation contract, dispatches read actions
                         (plan/drift/report) as one SigV4 POST /runs with the
                         status polled from openci-tf's run registry, drives
                         mutations (apply/destroy) through the PR state
                         machine on the write-back PR, and mints steps of kind
                         ssm_ec2_exec onto the existing `orders add host`
                         path. Every openci run id / comment id / order id is
                         persisted on the `pipeline_run` record before the
                         next side effect, so a killed run resumes from the
                         failed step when the order retries.
        notify_success / notify_failure
                         one typed run_result row through `config0 gitops
                         notify` (plan "Status producer"), key
                         `pipeline_run:<project_id>:<request_id>`; the work
                         job fails into notify_failure through on_failure.

    The user's PAT never rides this stack: the CLI verb reads it from the SSM
    clone-token path recorded on the openci-tf addon record.
    """

    def __init__(self, stackargs):
        newSchedStack.__init__(self, stackargs)

        # The SOURCE project's identity — saas-api resolves it at dispatch and
        # writes the pipeline_run record before placing this order.
        # Not "project_id" / "project_name": both are Stack built-ins bound to
        # the DISPATCH project (the internal project this stack runs under)
        # and the runtime refuses declared keys that shadow one (defect 34).
        self.parse.add_required(key="gitops_project_id", types="str")
        self.parse.add_required(key="gitops_project_name", types="str")
        self.parse.add_required(key="owner_id", types="str")
        self.parse.add_required(key="action", types="str",
                                choices=["plan", "drift", "report",
                                         "apply", "destroy"])
        self.parse.add_required(key="request_id", types="str")

        # Optional single-step targeting (read actions only; the verb refuses
        # it on mutations).
        self.parse.add_optional(key="step", default=None, types="str")

        # Status-producer identity (plan "Status producer" contract).
        self.parse.add_required(key="workflow_id", types="str")
        self.parse.add_required(key="attempt_id", types="str")

    def _init_common(self):
        import hashlib

        # The pipeline_run record's deterministic id — the same recipe the
        # config0_cli record builder applies
        # (md5("pipeline_run:" + project_id + ":" + request_id)).
        self.stack.set_variable(
            "run_resource_id",
            hashlib.md5(
                f"pipeline_run:{self.stack.gitops_project_id}:{self.stack.request_id}"
                .encode()).hexdigest())

    def _notify(self, status, error=None):
        """Emit the gitops status-producer order (`config0 gitops notify`)."""
        import shlex

        parts = [
            "config0", "gitops", "notify",
            f"workflow_id={self.stack.workflow_id}",
            f"owner={self.stack.owner_id}",
            "kind=run_result",
            f"key=pipeline_run:{self.stack.gitops_project_id}:{self.stack.request_id}",
            f"attempt_id={self.stack.attempt_id}",
            f"status={status}",
            f"resource_id={self.stack.run_resource_id}",
        ]
        if error:
            parts.append(f"error={error}")

        self.stack.add_external_cmd(
            cmd=" ".join(shlex.quote(part) for part in parts),
            role="gitops/notifier/execute",
            human_description=f"gitops pipeline run {status} notifier",
            display=True)

    def run_pipeline_run(self):
        import shlex

        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()

        parts = [
            "config0", "gitops", "pipeline-run",
            f"project_id={self.stack.gitops_project_id}",
            f"project_name={self.stack.gitops_project_name}",
            f"owner_id={self.stack.owner_id}",
            f"action={self.stack.action}",
            f"request_id={self.stack.request_id}",
        ]
        if self.stack.step:
            parts.append(f"step={self.stack.step}")
        self.stack.add_external_cmd(
            cmd=" ".join(shlex.quote(part) for part in parts),
            role="gitops/tenant/execute",
            human_description=f"gitops pipeline run: {self.stack.action}",
            display=True)
        return True

    def run_notify_success(self):
        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()
        self._notify("COMPLETED")
        return True

    def run_notify_failure(self):
        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()
        self._notify("FAILED", error="gitops pipeline run failed")
        return True

    def run(self):
        self.add_job("pipeline_run")
        self.add_job("notify_success")
        self.add_job("notify_failure")

        return self.finalize_jobs()

    def schedule(self):
        # pipeline_run -> notify_success; every failure exit reaches
        # notify_failure through on_failure. Nothing to destroy: the PR
        # comments and openci runs are retained history, and minted ssm host
        # orders settle inside this job's stage (they are its child orders).
        sched = self.new_schedule()
        sched.job = "pipeline_run"
        sched.archive.timeout = 4800
        sched.archive.timewait = 30
        sched.human_description = "gitops pipeline run: dispatch and drive"
        sched.on_success = ["notify_success"]
        sched.on_failure = ["notify_failure"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_success"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "gitops pipeline run: success notifier"
        sched.on_failure = ["notify_failure"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_failure"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "gitops pipeline run: failure notifier"
        self.add_schedule()

        return self.get_schedules()

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
    """Write a finished project's execution groups into the user's GitOps
    repo as one PR (plan "Write-back" contract, phase 5).

    One work job plus the gitops status-producer notifiers:

        writeback        `config0 gitops writeback ...` — the CLI verb does
                         everything: frontier check, replay-graph join,
                         translation, repo tree from the source zips, branch
                         `config0/<project>/<frontier_hash>`, one PR, one
                         summary comment, allowed_state_pairs registration,
                         the `pipeline` record. Idempotent on
                         `<project_id>:<frontier_hash>` — a duplicate run
                         returns the same PR.
        notify_success / notify_failure
                         one typed run_result row through `config0 gitops
                         notify` (plan "Status producer"); the work job fails
                         into notify_failure through on_failure.

    The user's PAT never rides this stack: the CLI verb reads it from the SSM
    clone-token path recorded on the openci-tf addon record.
    """

    def __init__(self, stackargs):
        newSchedStack.__init__(self, stackargs)

        # The SOURCE project's identity, FROZEN at its first dispatch —
        # saas-api passes it from the project_config row's data.gitops.
        # Not "project_id" / "project_name": both are Stack built-ins bound to
        # the DISPATCH project (the internal c0-writeback-<name> project this
        # stack runs under) and the runtime refuses declared keys that shadow
        # one. Under the built-in name the frontier check targeted the
        # dispatch project and could never see itself completed (defect 34).
        self.parse.add_required(key="gitops_project_id", types="str")
        self.parse.add_required(key="gitops_project_name", types="str")
        self.parse.add_required(key="owner_id", types="str")
        self.parse.add_required(key="repo_owner", types="str")   # GitHub owner
        self.parse.add_required(key="repo_name", types="str")    # bare repo name

        # Status-producer identity (plan "Status producer" contract).
        self.parse.add_required(key="workflow_id", types="str")
        self.parse.add_required(key="attempt_id", types="str")

        # Tenant state bucket; falls back to the worker-derived stateful bucket.
        self.parse.add_optional(key="state_bucket", default=None, types="str")

    def _init_common(self):
        import hashlib

        if not self.stack.state_bucket:
            self.stack.set_variable("state_bucket",
                                    self.stack.bucket_names["stateful"])

        # The pipeline record's deterministic id — the same recipe the
        # config0_cli record builder applies (md5("pipeline:" + project_id)).
        self.stack.set_variable(
            "pipeline_resource_id",
            hashlib.md5(f"pipeline:{self.stack.gitops_project_id}".encode()).hexdigest())

    def _notify(self, status, error=None):
        """Emit the gitops status-producer order (`config0 gitops notify`)."""
        import shlex

        parts = [
            "config0", "gitops", "notify",
            f"workflow_id={self.stack.workflow_id}",
            f"owner={self.stack.owner_id}",
            "kind=run_result",
            f"key=writeback:{self.stack.gitops_project_id}",
            f"attempt_id={self.stack.attempt_id}",
            f"status={status}",
            f"resource_id={self.stack.pipeline_resource_id}",
        ]
        if error:
            parts.append(f"error={error}")

        self.stack.add_external_cmd(
            cmd=" ".join(shlex.quote(part) for part in parts),
            role="gitops/notifier/execute",
            human_description=f"gitops write-back {status} notifier",
            display=True)

    def run_writeback(self):
        import shlex

        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()

        parts = [
            "config0", "gitops", "writeback",
            f"project_id={self.stack.gitops_project_id}",
            f"project_name={self.stack.gitops_project_name}",
            f"owner_id={self.stack.owner_id}",
            f"repo_owner={self.stack.repo_owner}",
            f"repo_name={self.stack.repo_name}",
            f"state_bucket={self.stack.state_bucket}",
        ]
        self.stack.add_external_cmd(
            cmd=" ".join(shlex.quote(part) for part in parts),
            role="gitops/tenant/execute",
            human_description="gitops write-back: assemble the repo tree and open the PR",
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
        self._notify("FAILED", error="gitops write-back failed")
        return True

    def run(self):
        self.add_job("writeback")
        self.add_job("notify_success")
        self.add_job("notify_failure")

        return self.finalize_jobs()

    def schedule(self):
        # writeback -> notify_success; every failure exit reaches
        # notify_failure through on_failure. Nothing to destroy: the PR,
        # branch and pipeline record outlive the run by design (plan
        # "Removal rules": retained GitHub history; records swept elsewhere).
        sched = self.new_schedule()
        sched.job = "writeback"
        sched.archive.timeout = 1800
        sched.archive.timewait = 30
        sched.human_description = "gitops write-back: repo tree + PR"
        sched.on_success = ["notify_success"]
        sched.on_failure = ["notify_failure"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_success"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "gitops write-back: success notifier"
        sched.on_failure = ["notify_failure"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_failure"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "gitops write-back: failure notifier"
        self.add_schedule()

        return self.get_schedules()

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
    """A removed project's gitops teardown, as its own HUB-frozen run.

    One work job:

        cleanup          `config0 gitops cleanup ...` - closes the project's
                         recorded PRs (write-back + mutation) with the add-on's
                         clone token and unregisters its state pairs from the
                         openci-tf settings table.

    Why a separate run (defect 49): a run executes in exactly ONE AWS account
    (aws-connections contract). The project's destroy run is frozen to the
    PROJECT's account, but the clone token (SSM) and the openci-tf-settings
    table exist only in the hub. saas-api's remove_project dispatches this
    stack frozen to the hub - the same shape as gitops_writeback - so the
    verb runs under gitops/tenant/execute with the hub's target session.

    The PR numbers ride as arguments: the pipeline / pipeline_run rows that
    carry them are swept by run_complete once the destroy completes, so this
    run never reads them. Nothing to destroy, nothing to notify: there is no
    card watching this run; its status is its own run row.
    """

    def __init__(self, stackargs):
        newSchedStack.__init__(self, stackargs)

        # The SOURCE project's identity - not "project_id": that is a Stack
        # built-in bound to the DISPATCH project (c0-cleanup-<name>).
        self.parse.add_required(key="gitops_project_id", types="str")
        self.parse.add_required(key="repo", types="str")  # owner/repo
        # Comma-separated PR numbers; absent when no PR was ever recorded.
        self.parse.add_optional(key="pr_numbers", default=None, types="str")

    def run_cleanup(self):
        import shlex

        self.stack.init_variables()
        self.stack.verify_variables()

        parts = [
            "config0", "gitops", "cleanup",
            f"project_id={self.stack.gitops_project_id}",
            f"repo={self.stack.repo}",
        ]
        if self.stack.pr_numbers:
            parts.append(f"pr_numbers={self.stack.pr_numbers}")

        self.stack.add_external_cmd(
            cmd=" ".join(shlex.quote(part) for part in parts),
            role="gitops/tenant/execute",
            human_description="gitops cleanup: close recorded PRs and unregister state pairs",
            display=True)
        return True

    def run(self):
        self.add_job("cleanup")
        return self.finalize_jobs()

    def schedule(self):
        sched = self.new_schedule()
        sched.job = "cleanup"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "gitops cleanup: PRs + state pairs"
        self.add_schedule()

        return self.get_schedules()

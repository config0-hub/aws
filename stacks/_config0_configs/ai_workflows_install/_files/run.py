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


class Main(newSchedStack):
    """Install the AI workflows add-on (provisional): record-only.

    The install creates nothing in AWS: no Terraform order, no server, no
    queue. `notify_success` writes the addon record inline; `notify_failure`
    reports a failed install through `config0 gitops notify`. run_complete
    reports Installed after the run is terminal. saas-api checks that a key
    input variable exists before dispatch; this stack reads no secret. A
    removal is the add-on project's `callback_delete` destroy, which never
    walks this stack's jobs, so no job has an `on_delete` edge.
    """

    # The owner_state.addons key (provisional): one AI workflows add-on per
    # owner, the openci_tf shape, so no region. agent_server's ADDON; a
    # server's key adds its hostname.
    ADDON = "ai_workflows"

    def __init__(self, stackargs):
        newSchedStack.__init__(self, stackargs)

        # The add-on identity run_complete and the notifier route read. Only
        # saas-api places this stack, so they are required.
        self.parse.add_required(key="workflow_id", types="str")
        self.parse.add_required(key="attempt_id", types="str")
        self.parse.add_required(key="owner_id", types="str")

    def _addon_resource_id(self):
        """The addon-record id (records contract): ``md5("addon:" + key)``."""
        import hashlib

        return hashlib.md5(f"addon:{self.ADDON}".encode()).hexdigest()

    def _notify(self, status, error=None):
        """Emit the gitops status-producer order (`config0 gitops notify`)."""
        import shlex

        parts = [
            "config0", "gitops", "notify",
            f"workflow_id={self.stack.workflow_id}",
            f"owner={self.stack.owner_id}",
            "kind=addon_result",
            f"key={self.ADDON}",
            f"attempt_id={self.stack.attempt_id}",
            f"status={status}",
            f"resource_id={self._addon_resource_id()}",
        ]
        if error:
            parts.append(f"error={error}")

        self.stack.add_external_cmd(
            cmd=" ".join(shlex.quote(part) for part in parts),
            role="gitops/notifier/execute",
            human_description=f"AI workflows add-on {status} notifier",
            display=True)

    def run_notify_success(self):
        """Write the addon record INLINE: the install's only effect."""
        stack = self.stack
        stack.init_variables()
        stack.verify_variables()

        addon_id = self._addon_resource_id()
        stack.record_resource(values={
            "_id": addon_id,
            "addon_id": addon_id,
            "resource_type": "addon",
            "provider": "config0",
            "name": self.ADDON,
            "addon": self.ADDON,
            "attempt_id": stack.attempt_id,
            "workflow_id": stack.workflow_id,
        })
        return True

    def run_notify_failure(self):
        self.stack.init_variables()
        self.stack.verify_variables()
        self._notify("FAILED", error="ai_workflows_install failed")
        return True

    def run(self):
        self.add_job("notify_success")
        self.add_job("notify_failure")

        return self.finalize_jobs()

    def schedule(self):
        sched = self.new_schedule()
        sched.job = "notify_success"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "Record the AI workflows add-on"
        sched.on_failure = ["notify_failure"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_failure"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "AI workflows add-on failure notifier"
        self.add_schedule()

        return self.get_schedules()

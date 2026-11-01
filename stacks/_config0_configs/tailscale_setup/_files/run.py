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

from config0_publisher.terraform import TFConstructor


class Main(newSchedStack):
    """Install the Tailscale add-on (provisional): check the user's tailnet policy.

    The `install` job runs one Terraform order with the Tailscale provider. It
    reads the policy and the device list, fails loud naming a missing policy
    entry, and writes nothing in the tailnet. The admin OAuth client reaches the
    provider only through `ssm_obj`. `notify_success` records the tailnet row and
    the addon record; `notify_failure` reports a failed install through
    `config0 gitops notify`. run_complete reports Installed after the run is
    terminal. A removal is the add-on project's `callback_delete` destroy, which
    never walks this stack's jobs, so no job has an `on_delete` edge.
    """

    # The owner_state.addons key (provisional): one Tailscale add-on per owner,
    # the openci_tf shape, so no region.
    ADDON = "tailscale"

    # The admin set's keys are the provider's own environment names, so the
    # env file the engine sources before every tofu command needs no renaming.
    ADMIN_KEYS = ("TAILSCALE_OAUTH_CLIENT_ID", "TAILSCALE_OAUTH_CLIENT_SECRET")

    def __init__(self, stackargs):
        newSchedStack.__init__(self, stackargs)

        # The input variable set saas-api references on the add-on schedule;
        # its keys arrive in stack.inputvars. Recorded on the tailnet row.
        self.parse.add_optional(key="admin_set_name",
                                default="tailscale_admin",
                                types="str")

        # The set a Tailscale server's instance role reads at boot. Recorded
        # on the tailnet row only; this stack never reads it.
        self.parse.add_optional(key="join_set_name",
                                default="tailscale_join",
                                types="str")

        self.parse.add_optional(key="tailscale_tag",
                                default="tag:config0",
                                tags="tfvar",
                                types="str")

        # The OS login the policy's ssh accept rule must name.
        self.parse.add_optional(key="ssh_login",
                                default="ubuntu",
                                tags="tfvar",
                                types="str")

        self.parse.add_optional(key="stateful_id",
                                default="_random")

        # The add-on identity run_complete and the notifier route read. Only
        # saas-api places this stack, so they are required.
        self.parse.add_required(key="workflow_id", types="str")
        self.parse.add_required(key="attempt_id", types="str")
        self.parse.add_required(key="owner_id", types="str")

        self.stack.add_execgroup("config0-hub:::aws::tailscale_setup",
                                 "tf_execgroup")

        self.stack.add_substack('config0-hub:::config0_core::tf_executor')

        self.stack.init_execgroups()
        self.stack.init_substacks()

    def _addon_resource_id(self):
        """The addon-record id (records contract): ``md5("addon:" + key)``."""
        import hashlib

        return hashlib.md5(f"addon:{self.ADDON}".encode()).hexdigest()

    def _admin_client(self):
        """The admin OAuth client from stack.inputvars, values decoded.

        Input variable values are entered base64. A missing key fails loud
        naming the key and the set, never a value.
        """
        import base64

        client = {}
        for key in self.ADMIN_KEYS:
            value = self.stack.inputvars.get(key)
            if not value:
                raise ValueError(
                    f"input variable set {self.stack.admin_set_name} has no {key}"
                )
            client[key] = base64.b64decode(value, validate=True).decode()
        return client

    def run_install(self):
        stack = self.stack

        stack.init_variables()
        stack.verify_variables()

        tf = TFConstructor(stack=stack,
                           execgroup_name=stack.tf_execgroup.name,
                           provider="tailscale",
                           resource_name=self.ADDON,
                           ssm_obj=self._admin_client(),
                           resource_type="tailscale_setup")

        tf.include(values={"addon_id": self._addon_resource_id()})
        tf.include(keys=["tailscale_tag"])
        tf.output(keys=["tailscale_tag"])

        stack.tf_executor.insert(display=True, **tf.get())

        return True

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
            human_description=f"Tailscale add-on {status} notifier",
            display=True)

    def run_notify_success(self):
        """Record the tailnet row, then the addon record, INLINE.

        The tag comes from the install's terraform row, the output of the
        checked policy; the set names from the arguments. The device read stays
        in the execgroup as the scope proof and lands on no row.
        No value of either set is recorded. The addon record is written last,
        so it never stands without its tailnet row.
        """
        import hashlib

        stack = self.stack
        stack.init_variables()
        stack.verify_variables()

        checked = stack.get_resource(resource_type="tailscale_setup",
                                     ref_schedule_id=stack.schedule_id,
                                     must_be_one=True,
                                     overlay_tfstate=False)[0]

        addon_id = self._addon_resource_id()
        stack.record_resource(values={
            "_id": hashlib.md5(
                f"addon_resource:{addon_id}:tailnet:{self.ADDON}".encode()
            ).hexdigest(),
            "resource_type": "tailnet",
            "provider": "tailscale",
            "name": self.ADDON,
            "addon": self.ADDON,
            "addon_id": addon_id,
            "tailscale_tag": checked["tailscale_tag"],
            "admin_set_name": stack.admin_set_name,
            "join_set_name": stack.join_set_name,
        })
        stack.record_resource(values={
            "_id": addon_id,
            "addon_id": addon_id,
            "resource_type": "addon",
            "provider": "tailscale",
            "name": self.ADDON,
            "addon": self.ADDON,
            "attempt_id": stack.attempt_id,
            "workflow_id": stack.workflow_id,
        })
        return True

    def run_notify_failure(self):
        self.stack.init_variables()
        self.stack.verify_variables()
        self._notify("FAILED", error="tailscale_setup failed")
        return True

    def run(self):
        self.add_job("install")
        self.add_job("notify_success")
        self.add_job("notify_failure")

        return self.finalize_jobs()

    def schedule(self):
        sched = self.new_schedule()
        sched.job = "install"
        sched.archive.timeout = 1800
        sched.archive.timewait = 120
        sched.human_description = "Check the Tailscale policy and device scope"
        sched.on_success = ["notify_success"]
        sched.on_failure = ["notify_failure"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_success"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "Tailscale add-on success notifier"
        sched.on_failure = ["notify_failure"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_failure"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "Tailscale add-on failure notifier"
        self.add_schedule()

        return self.get_schedules()

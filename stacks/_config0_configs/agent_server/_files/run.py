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
    """Create one agent server (provisional) and its own SQS queue.

    The `server` job runs one Terraform order on the `agent_server` execgroup:
    the instance role and profile, the security group, the instance and the
    queue. By default the server sits in a private subnet with no inbound
    port, no key pair and no public address, and is reached over Session
    Manager. A private subnet without NAT egress fails the plan before the
    server exists. The port 22 option first uploads a key pair through
    `ec2_ssh_upload`, from the SSH set's `public_key` in stack.inputvars.

    With Tailscale on, the server joins the customer's tailnet at first boot:
    its instance role reads the `tailscale_join` set by name, and its user
    data carries the parameter path, never a secret. After the server order,
    a `tailscale_device` substack order reads the device with the
    `tailscale_admin` client from stack.inputvars; its row is newer than the
    server row, so delete a server deletes the device first.

    `notify_success` copies the device's Tailscale fields onto the server row
    and records the server's addon record only when the add-on route set the
    identity; `notify_failure` reports a failed run through
    `config0 gitops notify`. Delete a server is the add-on project's
    `callback_delete` destroy, which never walks this stack's jobs, so no job
    has an `on_delete` edge.
    """

    # The add-on whose servers this stack records (provisional), the
    # ai_workflows_install stack's ADDON. A server's key adds its hostname.
    ADDON = "ai_workflows"

    # The tailscale_admin set's keys, which tailscale_device passes as ssm_obj.
    TAILSCALE_ADMIN_KEYS = ("TAILSCALE_OAUTH_CLIENT_ID", "TAILSCALE_OAUTH_CLIENT_SECRET")

    # The device fields notify_success copies onto the server row.
    TAILSCALE_DEVICE_KEYS = ("tailscale_hostname", "tailscale_tag", "tailscale_node_id")

    def __init__(self, stackargs):
        newSchedStack.__init__(self, stackargs)

        # Names the instance and its role, profile, security group and queue.
        self.parse.add_required(key="hostname",
                                tags="tfvar,db",
                                types="str")

        # Private by default: the run fails before the server exists unless
        # the subnet's route table sends 0.0.0.0/0 to a NAT gateway.
        self.parse.add_required(key="subnet_id",
                                tags="tfvar,db",
                                types="str")

        # The public-subnet option: a public address, no NAT egress check.
        # aws_ec2_server defaults its public address to true; this stack does not.
        self.parse.add_optional(key="public_subnet",
                                default="false",
                                tags="tfvar",
                                types="bool")

        self.parse.add_required(key="aws_default_region",
                                tags="tfvar,resource,db,tf_exec_env",
                                types="str")

        # Instance size inputs, as aws_ec2_server takes them.
        self.parse.add_optional(key="instance_type",
                                default="t3.micro",
                                tags="tfvar,db",
                                types="str")

        self.parse.add_optional(key="ami_filter",
                                default='ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*',
                                tags="tfvar",
                                types="str")

        # default is canonical
        self.parse.add_optional(key="ami_owner",
                                default='099720109477',
                                tags="tfvar",
                                types="str")

        self.parse.add_optional(key="disktype",
                                default="gp2",
                                tags="tfvar",
                                types="str")

        self.parse.add_optional(key="disksize",
                                default="20",
                                tags="tfvar",
                                types="int")

        # The port 22 option, off by default. On, it needs the CIDR and the
        # name of the SSH input variable set saas-api references on the
        # schedule; the public key arrives in stack.inputvars, never as an
        # argument.
        self.parse.add_optional(key="ssh_enabled",
                                default="false",
                                types="bool")

        self.parse.add_optional(key="ssh_cidr",
                                types="str")

        self.parse.add_optional(key="ssh_set_name",
                                types="str")

        # The key input variable sets the instance role may read, each by
        # name, never the input-variable prefix.
        self.parse.add_optional(key="key_set_names",
                                default="CLAUDE_CODE_OAUTH_TOKEN,ANTHROPIC_API_KEY,OPENAI_API_KEY",
                                types="str")

        # Tailscale, off by default; the add-on route turns it on. On, the
        # instance role also reads the join set by name and the server joins
        # at boot. The admin set reaches stack orders only, through the
        # reference row saas-api writes on the schedule; the join set is never
        # a reference.
        self.parse.add_optional(key="tailscale_enabled",
                                default="false",
                                types="bool")

        self.parse.add_optional(key="tailscale_join_set_name",
                                default="tailscale_join",
                                types="str")

        self.parse.add_optional(key="tailscale_admin_set_name",
                                default="tailscale_admin",
                                types="str")

        self.parse.add_optional(key="tailscale_tag",
                                default="tag:config0",
                                types="str")

        # The server row's labels_lifetime (provisional): a selection
        # convention, permanent for the add-on's servers.
        self.parse.add_required(key="lifetime",
                                default="permanent",
                                choices=["per_run", "permanent"],
                                types="str")

        # The add-on identity run_complete and the notifier route read. Set
        # only when saas-api places the server from the add-on card; an
        # author's composition leaves them unset and no addon record is written.
        self.parse.add_optional(key="workflow_id", default=None, types="str")
        self.parse.add_optional(key="attempt_id", default=None, types="str")
        self.parse.add_optional(key="owner_id", default=None, types="str")

        self.stack.add_execgroup("config0-hub:::aws::agent_server",
                                 "tf_execgroup")

        self.stack.add_substack('config0-hub:::config0_core::tf_executor')
        self.stack.add_substack('config0-hub:::aws::ec2_ssh_upload')
        self.stack.add_substack('config0-hub:::aws::tailscale_device')

        self.stack.init_execgroups()
        self.stack.init_substacks()

    def _addon_identity_set(self):
        """True only when the add-on route set the identity.

        The legacy "null"/"None" strings are TRUTHY, so they count as unset
        (the ssm_ec2_exec_eventbridge_install guard).
        """
        attempt_id = str(self.stack.attempt_id or "")
        return attempt_id.lower() not in ("", "none", "null")

    def _addon_key(self):
        """The server's owner_state.addons key: the add-on's key with the hostname."""
        return f"{self.ADDON}:{self.stack.hostname}"

    def _addon_resource_id(self):
        """The addon-record id (records contract): ``md5("addon:" + key)``."""
        import hashlib

        return hashlib.md5(f"addon:{self._addon_key()}".encode()).hexdigest()

    def _inputvars_path(self, name):
        """One input variable set's SSM path, /config0/{owner_id}/inputvars/{name}."""
        import os

        owner_id = os.environ.get("CONFIG0_OWNER_ID")
        if not owner_id:
            raise ValueError("CONFIG0_OWNER_ID environment variable is required")
        return f"/config0/{owner_id}/inputvars/{name}"

    def _key_parameter_paths(self):
        """The SSM paths of the named sets the instance role reads, comma-delimited for the tfvar.

        The key sets, and the join set with Tailscale on. A name that could
        widen the grant fails loud, and so does the admin set: the instance
        role never reads it.
        """
        stack = self.stack

        names = [("key_set_names", name.strip()) for name in stack.key_set_names.split(",")]
        if stack.tailscale_enabled:
            names.append(("tailscale_join_set_name", stack.tailscale_join_set_name))
        for argument, name in names:
            if not name or any(char in name for char in "*?/"):
                raise ValueError(
                    f"{argument} must name each set, never a prefix or pattern: {name!r}"
                )
            if name == stack.tailscale_admin_set_name:
                raise ValueError(
                    f"{argument} names the admin set {name}; the instance role never reads it"
                )
        return ",".join(self._inputvars_path(name) for _, name in names)

    def _set_tailscale_boot(self):
        """Tailscale on: the boot join's tfvars, after checking the admin client.

        The admin keys are checked before any order, so a server never stands
        joined with no device order that could delete its device.
        """
        stack = self.stack

        for key in self.TAILSCALE_ADMIN_KEYS:
            if not stack.inputvars.get(key):
                raise ValueError(
                    f"input variable set {stack.tailscale_admin_set_name} has no {key}"
                )

        stack.set_variable("tailscale_join_parameter_path",
                           self._inputvars_path(stack.tailscale_join_set_name),
                           tags="tfvar",
                           types="str")
        stack.parse.tag_key(key="tailscale_tag", tags="tfvar")

    def _insert_key_pair(self):
        """The port 22 option: upload the key pair, then open 22 to the CIDR.

        ec2_ssh_upload reads the public key from the SSH set's stack.inputvars,
        as it does for any stack order of the schedule, so the key never rides
        an argument.
        """
        stack = self.stack

        for key in ("ssh_cidr", "ssh_set_name"):
            if not stack.get_attr(key):
                raise ValueError(f"ssh_enabled needs {key}")

        if not stack.inputvars.get("public_key"):
            raise ValueError(
                f"input variable set {stack.ssh_set_name} has no public_key"
            )

        key_name = f"agent-server-{stack.hostname}"
        stack.ec2_ssh_upload.insert(
            display=True,
            arguments={"key_name": key_name,
                       "aws_default_region": stack.aws_default_region},
            human_description=f"Upload the SSH key pair {key_name}")

        stack.set_variable("ssh_key_name",
                           key_name,
                           tags="tfvar",
                           types="str")
        stack.parse.tag_key(key="ssh_cidr", tags="tfvar")

    def run_server(self):
        stack = self.stack

        stack.init_variables()
        stack.verify_variables()

        stack.set_variable("key_parameter_paths",
                           self._key_parameter_paths(),
                           tags="tfvar",
                           types="str")

        if stack.tailscale_enabled:
            self._set_tailscale_boot()

        if stack.ssh_enabled:
            self._insert_key_pair()
        elif stack.get_attr("ssh_cidr") or stack.get_attr("ssh_set_name"):
            raise ValueError("ssh_cidr and ssh_set_name need ssh_enabled")

        tf = TFConstructor(stack=stack,
                           execgroup_name=stack.tf_execgroup.name,
                           provider="aws",
                           resource_name=stack.hostname,
                           resource_type="server")

        values = {
            "aws_default_region": stack.aws_default_region,
            "hostname": stack.hostname,
        }
        if self._addon_identity_set():
            # The add-on identity stamp: the same addon_id the server's addon
            # record carries.
            values["addon_id"] = self._addon_resource_id()
        if stack.tailscale_enabled:
            # On the server row from its own order, so uninstall's refusal
            # sees it even if the device capture fails.
            values["tailscale"] = True
        tf.include(values=values)

        tf.include(values={"labels": {"lifetime": stack.lifetime}})

        # The server record's ids, as aws_ec2_server promotes them, with the
        # instance role and the server's own queue URL beside them.
        tf.include(keys=["account_id",
                         "region",
                         "instance_id",
                         "instance_profile",
                         "iam_role_arn",
                         "queue_url"])

        # resource output to show on saas ui
        tf.output(keys=["instance_id", "private_ip", "public_ip", "queue_url"])

        stack.tf_executor.insert(display=True, **tf.get())

        if stack.tailscale_enabled:
            # After the server order, so its row is newer than the server row.
            stack.tailscale_device.insert(
                display=True,
                arguments={"hostname": stack.hostname,
                           "tailscale_tag": stack.tailscale_tag,
                           "admin_set_name": stack.tailscale_admin_set_name},
                human_description=f"Capture the Tailscale device {stack.hostname}")

        return True

    def _record_tailscale_device(self):
        """Copy the device row's Tailscale fields onto the server row (gap G3).

        Through the resource upsert, which keeps the server row's created_at,
        so the device row stays the newer one for the newest-first destroy.
        """
        stack = self.stack

        device = stack.get_resource(resource_type="tailscale_device",
                                    name=stack.hostname,
                                    ref_schedule_id=stack.schedule_id,
                                    must_be_one=True,
                                    overlay_tfstate=False)[0]
        server = stack.get_resource(resource_type="server",
                                    name=stack.hostname,
                                    ref_schedule_id=stack.schedule_id,
                                    must_be_one=True,
                                    overlay_tfstate=False)[0]

        # tailscale rides again as a JSON true, the value uninstall's scan matches.
        stack.update_resource({"tailscale": True,
                               **{key: device[key] for key in self.TAILSCALE_DEVICE_KEYS}},
                              **server)

    def _notify(self, status, error=None):
        """Emit the gitops status-producer order (`config0 gitops notify`).

        Without the add-on identity, workflow_id is empty and the notify
        command states there is nothing to write.
        """
        import shlex

        parts = [
            "config0", "gitops", "notify",
            f"workflow_id={self.stack.workflow_id or ''}",
            f"owner={self.stack.owner_id or ''}",
            "kind=addon_result",
            f"key={self._addon_key()}",
            f"attempt_id={self.stack.attempt_id or ''}",
            f"status={status}",
            f"resource_id={self._addon_resource_id()}",
        ]
        if error:
            parts.append(f"error={error}")

        self.stack.add_external_cmd(
            cmd=" ".join(shlex.quote(part) for part in parts),
            role="gitops/notifier/execute",
            human_description=f"AI workflows server {status} notifier",
            display=True)

    def run_notify_success(self):
        """The Tailscale fields onto the server row, then the server's addon record, INLINE.

        The addon record is written only on the add-on path, and last, so it
        never stands without the server row's Tailscale fields.
        """
        stack = self.stack
        stack.init_variables()
        stack.verify_variables()

        if stack.tailscale_enabled:
            self._record_tailscale_device()

        if self._addon_identity_set():
            addon_id = self._addon_resource_id()
            stack.record_resource(values={
                "_id": addon_id,
                "addon_id": addon_id,
                "resource_type": "addon",
                "provider": "aws",
                "name": stack.hostname,
                "addon": self.ADDON,
                "hostname": stack.hostname,
                "attempt_id": stack.attempt_id,
                "workflow_id": stack.workflow_id or "",
            })
        return True

    def run_notify_failure(self):
        self.stack.init_variables()
        self.stack.verify_variables()
        self._notify("FAILED", error="agent_server failed")
        return True

    def run(self):
        self.add_job("server")
        self.add_job("notify_success")
        self.add_job("notify_failure")

        return self.finalize_jobs()

    def schedule(self):
        sched = self.new_schedule()
        sched.job = "server"
        sched.archive.timeout = 1800
        sched.archive.timewait = 120
        sched.human_description = "Create the agent server and its queue"
        sched.on_success = ["notify_success"]
        sched.on_failure = ["notify_failure"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_success"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "AI workflows server success notifier"
        sched.on_failure = ["notify_failure"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_failure"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "AI workflows server failure notifier"
        self.add_schedule()

        return self.get_schedules()

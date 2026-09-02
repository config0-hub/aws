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


def _set_codebuild_image(stack):

    if stack.runtime == "python3.9":
        stack.set_variable("build_image",
                           'aws/codebuild/standard:5.0')
    elif stack.runtime == "python3.10":
        stack.set_variable("build_image",
                           'aws/codebuild/standard:6.0')
    elif stack.runtime == "python3.11":
        stack.set_variable("build_image",
                           'aws/codebuild/standard:7.0')
    else:
        stack.set_variable("build_image",
                           'aws/codebuild/standard:7.0')


class Main(newSchedStack):
    """Install the SSM EC2 executor (eventbridge) into the tenant account.

    One `install` job carries the original two orders (CodeBuild lambda build,
    then the vendored terraform through tf_executor). The add-on flow (plan
    phase 3) adds the gitops status-producer stages: `notify_success` /
    `notify_failure` write one typed addon_result row (kind `ssm_ec2_exec`,
    the region as the add-on key) through `config0 gitops notify`; the install
    job fails into the failure notifier through on_failure. An onboarding
    placement passes no workflow_id — the notifier command then states there is
    no subscriber and writes nothing.
    """

    def __init__(self, stackargs):
        newSchedStack.__init__(self, stackargs)

        # aws_region matches the vendored terraform's variable.aws_region
        self.parse.add_optional(key="aws_region",
                                default="ap-northeast-1",
                                tags="tfvar",
                                types="str")

        # The dedicated Lambda-artifacts bucket is a SEPARATE stack
        # (aws_s3_bucket, resource_type cloud_storage). The config0.yaml supplies
        # its name here as a selector expression; this run.py treats it as a plain
        # input var and feeds it to both the CodeBuild upload and the terraform.
        self.parse.add_required(key="s3_bucket",
                                tags="tfvar",
                                types="str")

        # This install stack is NOT an account-wide singleton: install_name
        # discriminates every AWS resource name it creates (and the resource
        # record's identity below) so more than one install can coexist in one
        # account. Optional, default "main": a single install stays zero-config;
        # a second install in the same account passes a distinct install_name.
        # Two installs sharing one collide on create.
        self.parse.add_optional(key="install_name",
                                default="main",
                                tags="tfvar",
                                types="str")

        # codebuild framing (aws-lambda-python-codebuild optionals)
        self.parse.add_optional(key="runtime",
                                default="python3.12",
                                types="str")

        self.parse.add_optional(key="compute_type",
                                types="str",
                                default="BUILD_GENERAL1_SMALL")

        self.parse.add_optional(key="image_type",
                                types="str",
                                default="LINUX_CONTAINER")

        self.parse.add_optional(key="build_timeout",
                                types="int",
                                default=600)  # MUST stay a literal: stack introspection reconstructs
                                              # declaration lines only, so a module constant here
                                              # resolves to a mock and breaks the scan

        self.parse.add_optional(key="codebuild_role",
                                default="config0-assume-poweruser")

        self.parse.add_optional(key="cloud_tags_hash",
                                default='null')

        self.parse.add_optional(key="stateful_id",
                                default="_random")

        self.parse.add_optional(key="execution_id",
                                default=None)  # None registers the key unset; the legacy "null"
                                               # string is TRUTHY in the rewrite, so the
                                               # if-not-execution_id resolution below never fired
                                               # and the buildspec baked executions/null/done

        self.parse.add_optional(key="share_dir",
                                default="/var/tmp/share")

        self.parse.add_optional(key="script_name",
                                default="docker-to-lambda.sh")  # script name to run in codebuild

        # gitops status-producer context (plan "Status producer" contract).
        # Present only when saas-api places the install as an add-on
        # (POST /addons/ssm-ec2-executor); the onboarding placement leaves
        # them unset and the notifier writes nothing.
        self.parse.add_optional(key="workflow_id", default=None, types="str")
        self.parse.add_optional(key="attempt_id", default=None, types="str")
        self.parse.add_optional(key="owner_id", default=None, types="str")

        # declare execution groups
        self.stack.add_execgroup("config0-hub:::aws::ssm_ec2_exec_eventbridge_lambda_build",
                                 "lambda_build")

        self.stack.add_execgroup("config0-hub:::aws::ssm_ec2_exec_eventbridge_install",
                                 "tf_execgroup")

        # add substacks
        self.stack.add_substack('config0-hub:::config0_core::tf_executor')
        self.stack.add_substack(
            'config0-hub:::aws_storage::aws_s3_bucket',
            'lambda_artifacts_bucket',
        )

        # initialize
        self.stack.init_execgroups()
        self.stack.init_substacks()

    def run_bucket(self):
        """Create the region-local Lambda artifact bucket before CodeBuild."""
        stack = self.stack
        stack.init_variables()
        stack.verify_variables()
        # SubstackAdd.insert has a CLOSED signature: the child stack's args ride
        # the ``arguments=`` dict (the setup_codebuild_ci / legacy add_codebuild_ci
        # pattern), never flat kwargs — those raise TypeError and no order emits.
        arguments = {
            "bucket": stack.s3_bucket,
            "acl": "private",
            "versioning": "true",
            "force_destroy": "true",
            "aws_default_region": stack.aws_region,
        }
        stack.lambda_artifacts_bucket.insert(
            display=True,
            arguments=arguments,
            human_description=f"Create s3 bucket {stack.s3_bucket} for Lambda artifacts",
        )
        return True

    def run_install(self):

        import json
        import os

        stack = self.stack

        stack.init_variables()
        stack.verify_variables()

        if not stack.execution_id and os.environ.get("EXECUTION_ID"):
            stack.set_variable("execution_id", os.environ["EXECUTION_ID"])
        elif not stack.execution_id:
            stack.set_variable("execution_id", stack.stateful_id)

        _set_codebuild_image(stack)

        stack.set_variable("run_share_dir",
                           os.path.join(stack.share_dir,
                           stack.stateful_id))

        # execution-scoped key prefix: a fresh build lands the zips under a new
        # prefix -> terraform sees a changed s3_key -> the Lambda redeploys.
        key_prefix = f"{stack.execution_id}/"

        # ---------------------------------------------------------------------
        # ORDER 1 (CodeBuild): build the three Lambda zips with docker-to-lambda.sh
        # and upload them to the selected bucket under key_prefix. The script loops
        # starter/callback/fallback, so there is no per-lambda name here.
        # ---------------------------------------------------------------------
        build_envs = {
            'PYTHON_VERSION': stack.runtime.split("python")[1],
            'S3_BUCKET': stack.s3_bucket,
            'KEY_PREFIX': key_prefix,
            'UPLOAD_TO_S3': "true",  # renamed: the submitter strips reserved ^CODEBUILD_* vars
            'STATEFUL_ID': stack.stateful_id,
            'EXECUTION_ID': stack.execution_id,
            'TMP_BUCKET': stack.tmp_bucket,
            'SHARE_DIR': stack.share_dir,
            'WORKING_SUBDIR': 'var/tmp/lambda',
            'RUN_SHARE_DIR': stack.run_share_dir,
            'CHROOTFILES_DEST_DIR': stack.run_share_dir,
            'WORKING_DIR': stack.run_share_dir,
            'BUILD_IMAGE': stack.build_image,
            'CODEBUILD_COMPUTE_TYPE': stack.compute_type,
            'SCRIPT_NAME': stack.script_name,  # rides the SOPS-sealed env; the engine build
                                               # runs ${SCRIPT_NAME:-docker-to-lambda.sh}
                                               # (codebuild_srcfile_helper.py SRCFILE_BUILD_CMDS)
            'BUILD_TIMEOUT': stack.build_timeout,
            'DIRECT': "True",  # direct-mode engine delivery (execution_mode="direct"):
                               # CodeBuild standard:7.0 privileged + S3 engine.zip,
                               # required for the docker build inside the container
                               # (codebuild_srcfile_helper.py reads this via the
                               # CODEBUILD_PARAMS_HASH channel)
            'USE_CODEBUILD': "True",
            "AWS_DEFAULT_REGION": stack.aws_region
        }

        env_vars = {
            'CODEBUILD_PARAMS_HASH': stack.serialize({
                "env_vars": build_envs,
                "build_env_vars": build_envs}, json=False),
            'CHROOTFILES_DEST_DIR': stack.run_share_dir,
            "AWS_DEFAULT_REGION": stack.aws_region,
            'WORKING_DIR': stack.run_share_dir,
            'APP_NAME': "lambda",
            'APP_DIR': "var/tmp/lambda"
        }

        # The order's timeout drives BOTH the worker's done-marker watch deadline
        # and the target-account session it mints (config0-worker
        # internal/consumer: engineWatchTimeout / targetCredsDuration - deadline
        # plus margin, bounded by the 3600s AWS role-chaining cap (the hub mints
        # chained sessions, so max_session_duration does not lift it), fail loud
        # past it). Ask for the build's own timeout plus queue/provisioning
        # headroom; no clamp here.
        order_timeout = int(stack.build_timeout) + 600

        inputargs = {
            "name": "ssm_ec2_exec_eventbridge_lambdas",
            "env_vars": json.dumps(env_vars),
            "timeout": order_timeout
        }

        if stack.cloud_tags_hash:
            inputargs["cloud_tags_hash"] = stack.cloud_tags_hash

        inputargs["use_docker"] = "True"

        stack.lambda_build.insert(**inputargs)

        # ---------------------------------------------------------------------
        # ORDER 2 (terraform): the full vendored module. The three Lambdas
        # reference the zips uploaded in order 1 by s3_bucket + s3_key_*.
        # ---------------------------------------------------------------------
        # The three s3_key_* are computed from key_prefix; tag them tfvar so they
        # become TF_VAR_s3_key_* (include(values=) alone only records them on the
        # resource surface, it does not feed terraform). set_variable records them
        # in set_vars_manual so the TFConstructor reset never clobbers them.
        stack.set_variable("s3_key_starter", f"{key_prefix}starter.zip", tags="tfvar")
        stack.set_variable("s3_key_callback", f"{key_prefix}callback.zip", tags="tfvar")
        stack.set_variable("s3_key_fallback", f"{key_prefix}fallback.zip", tags="tfvar")

        tf = TFConstructor(stack=stack,
                           execgroup_name=stack.tf_execgroup.name,
                           provider="aws",
                           resource_name=f"ssm_ec2_exec_eventbridge-{stack.install_name}",
                           resource_type="ssm_ec2_exec_eventbridge_install")

        tf.include(values={
            "aws_region": stack.aws_region,
            "s3_bucket": stack.s3_bucket,
            "s3_key_starter": f"{key_prefix}starter.zip",
            "s3_key_callback": f"{key_prefix}callback.zip",
            "s3_key_fallback": f"{key_prefix}fallback.zip",
            "install_name": stack.install_name
        })

        # Discovery contract: the host-order seam resolves the install record and
        # reads these promoted keys — never an order-payload override. Promote
        # them onto the queryable resource surface.
        tf.include(keys=["state_machine_arn",
                         "bucket_name",
                         "payload_key_layout",
                         "instance_profile_name",
                         "managed_tag_key",
                         "managed_tag_value",
                         "kms_key_arn"])

        # resource output to show on saas ui
        tf.output(keys=["state_machine_arn",
                        "bucket_name",
                        "instance_profile_name",
                        "dynamodb_table_name",
                        "kms_key_arn"])

        # finalize the tf_executor
        stack.tf_executor.insert(display=True,
                                 **tf.get())

        return True

    def _addon_resource_id(self):
        """The deterministic per-region addon-record id (records contract):
        ``_id = md5("addon:ssm_ec2_exec:" + region)``."""
        import hashlib

        return hashlib.md5(
            f"addon:ssm_ec2_exec:{self.stack.aws_region}".encode()
        ).hexdigest()

    def _notify(self, status, error=None):
        """Emit the gitops status-producer order (`config0 gitops notify`).

        The addon key is the region (`ssm_ec2_exec:<region>` — one SSM EC2
        executor add-on per region); the resource_id is the deterministic
        addon-record id for that key. When the install was not placed by an
        add-on workflow, workflow_id is empty and the notify command states
        there is nothing to write.
        """
        import shlex

        region = self.stack.aws_region
        parts = [
            "config0", "gitops", "notify",
            f"workflow_id={self.stack.workflow_id or ''}",
            f"owner={self.stack.owner_id or ''}",
            "kind=addon_result",
            f"key=ssm_ec2_exec:{region}",
            f"attempt_id={self.stack.attempt_id or ''}",
            f"status={status}",
            f"resource_id={self._addon_resource_id()}",
        ]
        if error:
            parts.append(f"error={error}")

        self.stack.add_external_cmd(
            cmd=" ".join(shlex.quote(part) for part in parts),
            role="gitops/notifier/execute",
            human_description=f"SSM EC2 executor add-on {status} notifier",
            display=True)

    def _record_addon(self):
        """Write the typed per-region ``addon`` row INLINE (records contract).

        The ONE row GET /addons, the attempt-fenced repair pass, and offboard
        query — same contract as the openci-tf branch's record stage. This job
        runs only on the install job's on_success edge, so the row exists only
        after a SUCCESSFUL install.
        """
        self.stack.record_resource(values={
            "_id": self._addon_resource_id(),
            "resource_type": "addon",
            "provider": "aws",
            "name": f"ssm_ec2_exec_eventbridge-{self.stack.install_name}",
            "addon": "ssm_ec2_exec",
            "region": self.stack.aws_region,
            "attempt_id": self.stack.attempt_id,
            "workflow_id": self.stack.workflow_id or "",
        })

    def _unrecord_addon(self):
        """Remove the typed addon row after a SUCCESSFUL destroy — idempotent
        (a repeated destroy finds no row and deletes nothing)."""
        rows = self.stack.get_resource(
            resource_type="addon", match={"_id": self._addon_resource_id()}
        )
        if rows:
            self.stack.unrecord_resource(_id=self._addon_resource_id())

    def run_notify_success(self):
        import os

        self.stack.init_variables()
        self.stack.verify_variables()

        destroy = os.environ.get("DESTROY", "").lower() in ("true", "1")
        # The typed addon row exists exactly while the add-on is installed:
        # written here on install success, removed here on destroy success.
        # An onboarding placement (no attempt_id) records nothing, matching
        # the notifier's no-subscriber rule. The legacy "null"/"None" strings
        # are TRUTHY (the execution_id gotcha above), so they count as unset.
        attempt_id = str(self.stack.attempt_id or "")
        if attempt_id.lower() not in ("", "none", "null"):
            if destroy:
                self._unrecord_addon()
            else:
                self._record_addon()
        # A destroy run (DESTROY=True in the run env, the same flag the
        # worker's on_delete walk keys off) reports the REMOVAL — owner-sync
        # maps REMOVED to the Convex ``removed`` addon status.
        self._notify("REMOVED" if destroy else "COMPLETED")
        return True

    def run_notify_failure(self):
        self.stack.init_variables()
        self.stack.verify_variables()
        self._notify("FAILED", error="ssm_ec2_exec_eventbridge_install failed")
        return True

    def run(self):
        self.add_job("bucket")
        self.add_job("install")
        self.add_job("notify_success")
        self.add_job("notify_failure")

        return self.finalize_jobs()

    def schedule(self):
        # Create the artifact bucket, install, then notify. Destroy reverses
        # ownership: install teardown first, artifact bucket second, then the
        # successful removal notification.
        sched = self.new_schedule()
        sched.job = "bucket"
        sched.archive.timeout = 1800
        sched.archive.timewait = 120
        sched.human_description = "Create SSM executor Lambda artifact bucket"
        sched.on_success = ["install"]
        sched.on_failure = ["notify_failure"]
        sched.on_delete = ["notify_success"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "install"
        sched.archive.timeout = 3600
        sched.archive.timewait = 120
        sched.human_description = "Install SSM EC2 executor (eventbridge)"
        sched.on_success = ["notify_success"]
        sched.on_failure = ["notify_failure"]
        sched.on_delete = ["bucket"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_success"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "SSM EC2 executor add-on success notifier"
        sched.on_failure = ["notify_failure"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_failure"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "SSM EC2 executor add-on failure notifier"
        self.add_schedule()

        return self.get_schedules()

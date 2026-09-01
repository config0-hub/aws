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
    """Install openci-tf into the tenant account as a config0 add-on.

    One scheduled job per install stage (plan "Install and removal"):

        ecr          installer --stage ecr (ECR repository via targeted apply)
        image_copy   GHCR -> tenant ECR image copy, delegated to CodeBuild
        deploy       installer --stage deploy (foundation + full deploy apply)
        token        GitHub clone token -> SSM /openci-tf/clone-token/<name>
        register     register_repo.py (webhook secret, settings, webhook)
        record       promote deploy outputs + registration values + attempt_id
                     onto the resources table (the addon record)
        notify_success / notify_failure
                     the gitops status producer: one typed addon_result row
                     through `config0 gitops notify`; every stage reaches the
                     failure notifier through on_failure

    Destroy walks the on_delete graph through registration, deploy, image,
    ECR, and record teardown with the token deleted LAST, then notify_success
    reports the removal.
    """

    def __init__(self, stackargs):
        newSchedStack.__init__(self, stackargs)

        # Identity of the add-on placement (saas-api supplies these when it
        # places the order). The PAT is deliberately NOT a stack argument:
        # arguments persist on QHost rows and exec orders, so the token rides
        # only the dispatch blob's secret channel (saas_params gitops_token).
        # The hub renders it into the encrypted run env as GITOPS_TOKEN; the
        # child process inherits it in memory and reseals it for engine execution.
        self.parse.add_required(key="repo", types="str")                 # owner/repo
        self.parse.add_required(key="ghcr_image", types="str")           # ghcr.io/...@sha256:<digest>
        self.parse.add_required(key="image_tag", types="str")            # the release IMAGE_VERSION
        self.parse.add_required(key="workflow_id", types="str")
        self.parse.add_required(key="attempt_id", types="str")
        self.parse.add_required(key="owner_id", types="str")
        # The tenant hub account's alias — one path segment of the decision-26
        # state key; the record stage promotes it onto the addon record
        # (the project-dispatch identity contract, projectlib/gitops.py).
        self.parse.add_required(key="account_alias", types="str")
        # The tenant executor role ARNs (config0-executor-local +
        # config0-executor-remote, comma-separated) that openci-tf's
        # api_caller_policy_json must authorize for plan|drift|report.
        # Required: an install without them deploys an EMPTY caller policy and
        # every day-2 read action is refused.
        self.parse.add_required(key="api_caller_role_arns", types="str")

        # Tenant plumbing: engine name and state bucket come from the hub
        # record via saas-api; the bucket falls back to the worker-derived
        # tenant hub bucket when not supplied.
        self.parse.add_optional(key="engine_name", default="config0-xe", types="str")
        self.parse.add_optional(key="remote_stateful_bucket", default=None, types="str")

        self.parse.add_optional(key="project_name", default="openci-tf", types="str")
        self.parse.add_optional(key="install_name", default="main", types="str")
        self.parse.add_optional(key="aws_default_region", default="ap-northeast-1", types="str")

        # trigger_id is optional at the surface: saas-api normally passes it;
        # a missing trigger_id derives a deterministic id below (best guess per
        # the plan's guiding rule, corrected while running the user story).
        self.parse.add_optional(key="trigger_id", default=None, types="str")

        # The pinned openci-tf source the engine-side stages clone.
        self.parse.add_optional(key="openci_tf_repo_url",
                                default="https://github.com/config0-hub/openci-tf.git",
                                types="str")
        self.parse.add_optional(
            key="openci_tf_git_ref",
            default="295b9371faed02486b3eaa8134f2104369902d44",
            types="str",
        )

        # codebuild framing for the image copy (mirrors
        # ssm_ec2_exec_eventbridge_install's lambda_build order)
        self.parse.add_optional(key="compute_type", types="str", default="BUILD_GENERAL1_SMALL")
        self.parse.add_optional(key="build_timeout", types="int", default=1200)
        self.parse.add_optional(key="cloud_tags_hash", default='null')
        self.parse.add_optional(key="stateful_id", default="_random")
        self.parse.add_optional(key="share_dir", default="/var/tmp/share")

        # declare execution groups
        self.stack.add_execgroup("config0-hub:::aws::openci-tf-addon",
                                 "addon_execgroup")
        self.stack.add_execgroup("config0-hub:::aws::openci-tf-image-copy",
                                 "image_copy_execgroup")

        self.stack.init_execgroups()

    def _init_common(self):
        """Derive the values every stage shares."""
        import hashlib
        import re

        if not self.stack.remote_stateful_bucket:
            self.stack.set_variable("remote_stateful_bucket",
                                    self.stack.bucket_names["stateful"])

        gh_owner, gh_repo = self.stack.repo.split("/", 1)

        # Clone-token SSM path (plan "Token" contract):
        # name = slug(owner_id-owner-repo)[:40] + "-" + sha256(owner_id/owner/repo)[:8]
        slug = re.sub(r"[^a-z0-9]+", "-",
                      f"{self.stack.owner_id}-{gh_owner}-{gh_repo}".lower()).strip("-")
        digest = hashlib.sha256(
            f"{self.stack.owner_id}/{gh_owner}/{gh_repo}".encode()).hexdigest()[:8]
        self.stack.set_variable("clone_token_ssm_path",
                                f"/openci-tf/clone-token/{slug[:40]}-{digest}")

        if not self.stack.trigger_id:
            self.stack.set_variable(
                "trigger_id",
                hashlib.sha256(
                    f"openci-tf-trigger:{self.stack.owner_id}/{self.stack.repo}".encode()
                ).hexdigest()[:16])

        # Deterministic addon-record id (one openci-tf install per account) —
        # the same recipe the config0_cli addon-record builder applies.
        self.stack.set_variable("addon_resource_id",
                                hashlib.md5(b"addon:openci_tf").hexdigest())

    def _stage_env_vars(self, stage):
        """The engine-side environment one openci-tf-addon stage order carries."""
        env_vars = {
            "STAGE": stage,
            "OPENCI_TF_REGION": self.stack.aws_default_region,
            "OPENCI_TF_PROJECT": self.stack.project_name,
            "OPENCI_TF_REPO_URL": self.stack.openci_tf_repo_url,
            "OPENCI_TF_GIT_REF": self.stack.openci_tf_git_ref,
            "STATE_BUCKET": self.stack.remote_stateful_bucket,
            "ENGINE_NAME": self.stack.engine_name,
            "TRIGGER_ID": self.stack.trigger_id,
            "GITOPS_REPO": self.stack.repo,
            "ACCOUNT_ALIAS": self.stack.account_alias,
            "CLONE_TOKEN_SSM_PATH": self.stack.clone_token_ssm_path,
            # ALWAYS forwarded (required argument): an empty caller policy
            # would refuse every day-2 plan|drift|report call.
            "API_CALLER_ROLE_ARNS": self.stack.api_caller_role_arns,
            "AWS_DEFAULT_REGION": self.stack.aws_default_region
        }
        return env_vars

    def _insert_stage(self, stage, timeout, extra_env_vars=None, human_description=None):
        import json

        env_vars = self._stage_env_vars(stage)
        if extra_env_vars:
            env_vars.update(extra_env_vars)

        inputargs = {
            "name": f"openci-tf-{self.stack.install_name}-{stage}",
            "env_vars": json.dumps(env_vars),
            "timeout": timeout
        }
        if self.stack.cloud_tags_hash:
            inputargs["cloud_tags_hash"] = self.stack.cloud_tags_hash
        if human_description:
            inputargs["human_description"] = human_description

        self.stack.addon_execgroup.insert(**inputargs)

    def _notify(self, status, error=None):
        """Emit the gitops status-producer order (`config0 gitops notify`)."""
        import shlex

        parts = [
            "config0", "gitops", "notify",
            f"workflow_id={self.stack.workflow_id}",
            f"owner={self.stack.owner_id}",
            "kind=addon_result",
            "key=openci_tf",
            f"attempt_id={self.stack.attempt_id}",
            f"status={status}",
            f"resource_id={self.stack.addon_resource_id}",
        ]
        if error:
            parts.append(f"error={error}")

        self.stack.add_external_cmd(
            cmd=" ".join(shlex.quote(part) for part in parts),
            role="gitops/notifier/execute",
            human_description=f"openci-tf add-on {status} notifier",
            display=True)

    def run_ecr(self):
        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()
        self._insert_stage(
            "ecr", 1800,
            human_description="openci-tf addon: create the ECR repository")
        return True

    def run_image_copy(self):
        import json
        import os

        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()

        self.stack.set_variable("run_share_dir",
                                os.path.join(self.stack.share_dir,
                                             self.stack.stateful_id))

        build_envs = {
            "GHCR_IMAGE": self.stack.ghcr_image,
            "ECR_IMAGE_TAG": self.stack.image_tag,
            "OPENCI_TF_PROJECT": self.stack.project_name,
            "STATEFUL_ID": self.stack.stateful_id,
            "TMP_BUCKET": self.stack.tmp_bucket,
            "SHARE_DIR": self.stack.share_dir,
            "WORKING_SUBDIR": "var/tmp/docker",
            "RUN_SHARE_DIR": self.stack.run_share_dir,
            "CHROOTFILES_DEST_DIR": self.stack.run_share_dir,
            "WORKING_DIR": self.stack.run_share_dir,
            "BUILD_IMAGE": "aws/codebuild/standard:7.0",
            "CODEBUILD_COMPUTE_TYPE": self.stack.compute_type,
            "SCRIPT_NAME": "copy-ghcr-to-ecr.sh",
            "BUILD_TIMEOUT": self.stack.build_timeout,
            "DIRECT": "True",  # privileged CodeBuild - docker pull/push inside
            "USE_CODEBUILD": "True",
            "AWS_DEFAULT_REGION": self.stack.aws_default_region,
            # CodeBuild receives a sealed environment rather than the parent
            # process environment, so the lifecycle method must be explicit.
            "METHOD": "destroy"
            if os.environ.get("DESTROY", "").lower() in ("true", "1")
            else "create",
        }

        env_vars = {
            "CODEBUILD_PARAMS_HASH": self.stack.serialize({
                "env_vars": build_envs,
                "build_env_vars": build_envs}, json=False),
            "CHROOTFILES_DEST_DIR": self.stack.run_share_dir,
            "AWS_DEFAULT_REGION": self.stack.aws_default_region,
            "WORKING_DIR": self.stack.run_share_dir,
            "APP_NAME": "docker",
            "APP_DIR": "var/tmp/docker"
        }

        inputargs = {
            "name": f"openci-tf-{self.stack.install_name}-image-copy",
            "env_vars": json.dumps(env_vars),
            "timeout": int(self.stack.build_timeout) + 600,
            "use_docker": "True",
            "human_description": "openci-tf addon: copy the GHCR image to tenant ECR"
        }
        if self.stack.cloud_tags_hash:
            inputargs["cloud_tags_hash"] = self.stack.cloud_tags_hash

        self.stack.image_copy_execgroup.insert(**inputargs)
        return True

    def run_deploy(self):
        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()
        self._insert_stage(
            "deploy", 3600,
            human_description="openci-tf addon: apply foundation and deploy")
        return True

    def run_token(self):
        import os

        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()

        destroying = os.environ.get("DESTROY", "").lower() in ("true", "1")
        if not destroying and not os.environ.get("GITOPS_TOKEN"):
            raise ValueError(
                "openci-tf addon install: GITOPS_TOKEN is missing from the "
                "encrypted run environment"
            )

        # The PAT remains in the encrypted run environment. The worker passes
        # that environment in memory to the child CLI process, and the execgroup
        # runtime seals it again for engine execution. The order carries no
        # token value, only the ordinary token-stage work.
        self._insert_stage(
            "token", 900,
            human_description=(
                "openci-tf addon: delete the clone token from SSM"
                if destroying
                else "openci-tf addon: store the clone token in SSM"
            ),
        )
        return True

    def run_register(self):
        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()
        self._insert_stage(
            "register", 1200,
            human_description=(
                "openci-tf addon: close pipeline PRs and remove registration"
                if self._destroying()
                else "openci-tf addon: register the repository and webhook"
            ),
        )
        return True

    def _destroying(self):
        import os

        return os.environ.get("DESTROY", "").lower() in ("true", "1")

    def run_record(self):
        import shlex

        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()

        if self._destroying():
            rows = self.stack.get_resource(match={"_id": self.stack.addon_resource_id})
            if rows:
                self.stack.unrecord_resource(_id=self.stack.addon_resource_id)
            else:
                print(
                    "openci-tf addon: record already absent after a prior "
                    "successful teardown attempt"
                )
            return True

        self._insert_stage(
            "record", 900,
            extra_env_vars={
                "ATTEMPT_ID": self.stack.attempt_id,
                "INSTALL_NAME": self.stack.install_name,
            },
            human_description="openci-tf addon: record the addon resource")

        # Reinstall re-registration (plan "Removal rules"): after the record
        # stage promoted settings_table_name onto the addon record, re-register
        # every same-repo pipeline's state pairs (a fresh install has no
        # pipelines — the verb states that and exits 0). Orders in one job run
        # sequentially, so this always follows the record stage. Skipped on the
        # destroy chain (the settings table is about to go).
        parts = [
            "config0", "gitops", "reregister",
            f"repo={self.stack.repo}",
            f"state_bucket={self.stack.remote_stateful_bucket}",
        ]
        self.stack.add_external_cmd(
            cmd=" ".join(shlex.quote(part) for part in parts),
            human_description="openci-tf addon: re-register pipeline state pairs",
            display=True,
        )
        return True

    def run_notify_success(self):
        import os

        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()
        # On a destroy run (the hub renders DESTROY=True into the run env, the
        # same flag the worker's on_delete walk keys off) the success notifier
        # reports the REMOVAL — owner-sync maps REMOVED to the Convex
        # ``removed`` addon status. An install run reports COMPLETED.
        if os.environ.get("DESTROY", "").lower() in ("true", "1"):
            self._notify("REMOVED")
        else:
            self._notify("COMPLETED")
        return True

    def run_notify_failure(self):
        self.stack.init_variables()
        self.stack.verify_variables()
        self._init_common()
        self._notify("FAILED", error="openci-tf add-on stage failed")
        return True

    def run(self):
        self.add_job("ecr")
        self.add_job("image_copy")
        self.add_job("deploy")
        self.add_job("token")
        self.add_job("register")
        self.add_job("record")
        self.add_job("notify_success")
        self.add_job("notify_failure")

        return self.finalize_jobs()

    def schedule(self):
        # Install chain: ecr -> image_copy -> deploy -> token -> register ->
        # record -> notify_success; every stage fails into notify_failure.
        # Destroy chain (on_delete, walked by a destroy run): register ->
        # deploy -> image_copy -> ecr -> token (LAST EXTERNAL SIDE EFFECT) ->
        # record -> notify_success reports the removal. The first destroy stage
        # is not a generic record-remove order, and the typed add-on row remains
        # as durable cleanup identity until token deletion succeeds.
        sched = self.new_schedule()
        sched.job = "ecr"
        sched.archive.timeout = 1800
        sched.archive.timewait = 120
        sched.human_description = "openci-tf addon: ECR repository"
        sched.on_success = ["image_copy"]
        sched.on_failure = ["notify_failure"]
        sched.on_delete = ["token"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "image_copy"
        sched.archive.timeout = 1800
        sched.archive.timewait = 120
        sched.human_description = "openci-tf addon: image copy GHCR -> ECR"
        sched.on_success = ["deploy"]
        sched.on_failure = ["notify_failure"]
        sched.on_delete = ["ecr"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "deploy"
        sched.archive.timeout = 4800
        sched.archive.timewait = 120
        sched.human_description = "openci-tf addon: foundation + deploy apply"
        sched.on_success = ["token"]
        sched.on_failure = ["notify_failure"]
        sched.on_delete = ["image_copy"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "token"
        sched.archive.timeout = 900
        sched.archive.timewait = 30
        sched.human_description = "openci-tf addon: clone token to SSM"
        sched.on_success = ["register"]
        sched.on_failure = ["notify_failure"]
        sched.on_delete = ["record"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "register"
        sched.archive.timeout = 1200
        sched.archive.timewait = 30
        sched.human_description = "openci-tf addon: repository registration"
        sched.on_success = ["record"]
        sched.on_failure = ["notify_failure"]
        sched.on_delete = ["deploy"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "record"
        sched.archive.timeout = 900
        sched.archive.timewait = 30
        sched.human_description = "openci-tf addon: resource record"
        sched.on_success = ["notify_success"]
        sched.on_failure = ["notify_failure"]
        sched.on_delete = ["notify_success"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_success"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "openci-tf addon: success notifier"
        sched.on_failure = ["notify_failure"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "notify_failure"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "openci-tf addon: failure notifier"
        self.add_schedule()

        return self.get_schedules()

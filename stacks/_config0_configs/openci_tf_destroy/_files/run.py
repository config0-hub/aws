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


def _init_common(stack):
    """Derive the values every stage shares - byte-identical to
    openci_tf_install._init_common (the clone-token path and trigger id MUST
    resolve to the names the install wrote)."""
    import hashlib
    import re

    if not stack.remote_stateful_bucket:
        stack.set_variable("remote_stateful_bucket",
                           stack.bucket_names["stateful"])

    gh_owner, gh_repo = stack.repo.split("/", 1)

    slug = re.sub(r"[^a-z0-9]+", "-",
                  f"{stack.owner_id}-{gh_owner}-{gh_repo}".lower()).strip("-")
    digest = hashlib.sha256(
        f"{stack.owner_id}/{gh_owner}/{gh_repo}".encode()).hexdigest()[:8]
    stack.set_variable("clone_token_ssm_path",
                       f"/openci-tf/clone-token/{slug[:40]}-{digest}")

    if not stack.trigger_id:
        stack.set_variable(
            "trigger_id",
            hashlib.sha256(
                f"openci-tf-trigger:{stack.owner_id}/{stack.repo}".encode()
            ).hexdigest()[:16])


def _stage_stateful_id(stack, stage):
    """The CodeBuild stage's own execution identity - byte-identical to
    openci_tf_install._stage_stateful_id, so each destroy stage lands on the
    execution slot, share dir and evidence files of the install stage it
    reverses, and never on another stage's (defect 24: the ecr destroy reused
    the deploy stage's id, hit its "existing run in progress", never ran, and
    passed on the deploy stage's leftover evidence)."""
    import hashlib

    seed = (
        f"openci-tf:{stack.owner_id}:{stack.repo}:"
        f"{stack.install_name}:{stack.aws_default_region}:{stage}"
    )
    return hashlib.md5(seed.encode()).hexdigest()[:16]


def _stage_env_vars(stack, stage):
    """The env one openci-tf-addon stage order carries (install recipe plus
    METHOD=destroy: the CLI's execgroup runtime and the stage script both
    read METHOD from the order env, and this stack only ever tears down)."""
    return {
        "STAGE": stage,
        "METHOD": "destroy",
        "OPENCI_TF_REGION": stack.aws_default_region,
        "OPENCI_TF_PROJECT": stack.openci_tf_project,
        "OPENCI_TF_REPO_URL": stack.openci_tf_repo_url,
        "OPENCI_TF_GIT_REF": stack.openci_tf_git_ref,
        "STATE_BUCKET": stack.remote_stateful_bucket,
        "ENGINE_NAME": stack.engine_name,
        "TRIGGER_ID": stack.trigger_id,
        "GITOPS_REPO": stack.repo,
        "ACCOUNT_ALIAS": stack.account_alias,
        "CLONE_TOKEN_SSM_PATH": stack.clone_token_ssm_path,
        "API_CALLER_ROLE_ARNS": stack.api_caller_role_arns,
        "AWS_DEFAULT_REGION": stack.aws_default_region
    }


def _insert_stage(stack, stage, timeout, human_description):
    """One Lambda-side openci-tf-addon-stage destroy order (token, register)."""
    import json

    inputargs = {
        "name": f"openci-tf-{stack.install_name}-{stage}",
        "env_vars": json.dumps(_stage_env_vars(stack, stage)),
        "timeout": timeout,
        "human_description": human_description
    }
    if stack.cloud_tags_hash:
        inputargs["cloud_tags_hash"] = stack.cloud_tags_hash

    stack.addon_execgroup.insert(**inputargs)


def _insert_tofu_stage(stack, stage, build_timeout, human_description):
    """One CodeBuild order running openci-tf-addon-tofu.py with METHOD=destroy
    (same codebuild-srcfile framing as the install; the script prints the
    CONFIG0_DESTROY_*_STATE_COUNT evidence the CLI finalizer reads)."""
    import json
    import os

    stateful_id = _stage_stateful_id(stack, stage)
    run_share_dir = os.path.join(stack.share_dir, stateful_id)

    build_envs = _stage_env_vars(stack, stage)
    build_envs.update({
        "TOFU_VERSION": stack.tofu_version,
        "STATEFUL_ID": stateful_id,
        "TMP_BUCKET": stack.tmp_bucket,
        "SHARE_DIR": stack.share_dir,
        "WORKING_SUBDIR": "var/tmp/openci-tf",
        "RUN_SHARE_DIR": run_share_dir,
        "CHROOTFILES_DEST_DIR": run_share_dir,
        "WORKING_DIR": run_share_dir,
        "CODEBUILD_COMPUTE_TYPE": stack.compute_type,
        "SCRIPT_NAME": "openci-tf-addon-tofu.py",
        "BUILD_TIMEOUT": build_timeout,
        "USE_CODEBUILD": "True",
    })

    env_vars = {
        "CODEBUILD_PARAMS_HASH": stack.serialize({
            "env_vars": build_envs,
            "build_env_vars": build_envs}, json=False),
        "CHROOTFILES_DEST_DIR": run_share_dir,
        "AWS_DEFAULT_REGION": stack.aws_default_region,
        "WORKING_DIR": run_share_dir,
        "APP_NAME": "openci-tf",
        "APP_DIR": "var/tmp/openci-tf"
    }

    inputargs = {
        "name": f"openci-tf-{stack.install_name}-{stage}",
        "env_vars": json.dumps(env_vars),
        "timeout": int(build_timeout) + 600,
        "human_description": human_description
    }
    if stack.cloud_tags_hash:
        inputargs["cloud_tags_hash"] = stack.cloud_tags_hash

    stack.tofu_execgroup.insert(**inputargs)


def _insert_image_copy(stack):
    """The CodeBuild image-copy order with METHOD=destroy (copy-ghcr-to-ecr.sh
    deletes the pushed tag and prints the destroy evidence markers)."""
    import json
    import os

    stateful_id = _stage_stateful_id(stack, "image-copy")
    run_share_dir = os.path.join(stack.share_dir, stateful_id)

    build_envs = {
        "METHOD": "destroy",
        "GHCR_IMAGE": stack.ghcr_image,
        "ECR_IMAGE_TAG": stack.image_tag,
        "OPENCI_TF_PROJECT": stack.openci_tf_project,
        "STATEFUL_ID": stateful_id,
        "TMP_BUCKET": stack.tmp_bucket,
        "SHARE_DIR": stack.share_dir,
        "WORKING_SUBDIR": "var/tmp/docker",
        "RUN_SHARE_DIR": run_share_dir,
        "CHROOTFILES_DEST_DIR": run_share_dir,
        "WORKING_DIR": run_share_dir,
        "BUILD_IMAGE": "aws/codebuild/standard:7.0",
        "CODEBUILD_COMPUTE_TYPE": stack.compute_type,
        "SCRIPT_NAME": "copy-ghcr-to-ecr.sh",
        "BUILD_TIMEOUT": stack.build_timeout,
        "DIRECT": "True",
        "USE_CODEBUILD": "True",
        "AWS_DEFAULT_REGION": stack.aws_default_region,
    }

    env_vars = {
        "CODEBUILD_PARAMS_HASH": stack.serialize({
            "env_vars": build_envs,
            "build_env_vars": build_envs}, json=False),
        "CHROOTFILES_DEST_DIR": run_share_dir,
        "AWS_DEFAULT_REGION": stack.aws_default_region,
        "WORKING_DIR": run_share_dir,
        "APP_NAME": "docker",
        "APP_DIR": "var/tmp/docker"
    }

    inputargs = {
        "name": f"openci-tf-{stack.install_name}-image-copy",
        "env_vars": json.dumps(env_vars),
        "timeout": int(stack.build_timeout) + 600,
        "use_docker": "True",
        "human_description": "openci-tf addon: delete the tenant ECR image tag"
    }
    if stack.cloud_tags_hash:
        inputargs["cloud_tags_hash"] = stack.cloud_tags_hash

    stack.image_copy_execgroup.insert(**inputargs)


def run(stackargs):
    """Tear an openci-tf add-on install down: the destroy INSTRUCTION the
    addon project's destroy anchor executes (saas-api ``ADDON_DESTROY_STACKS``;
    the anchor's schedule_vars carry the install's persistent arguments plus
    the removal attempt identity).

    The install records no per-stage resource rows, so the generic
    ``callback_delete`` teardown has nothing to remove; this Method Helper
    re-runs the install's own stages with METHOD=destroy as ONE sequential
    order chain in the explicit reverse install order (plan "Removal rules",
    token LAST):

        register     close pipeline PRs, delete the GitHub webhook, delete the
                     settings rows and webhook secret (needs the clone token)
        deploy       tofu destroy of the deploy and foundation roots
        image_copy   delete the pushed tenant ECR image tag
        ecr          tofu destroy of the ECR repository
        token        delete the clone token from SSM - the last external
                     side effect, so every earlier stage (and a retry of a
                     failed one) still finds it

    A failed order stops the chain; saas-api's run_complete destroy gate keeps
    every row (the addon record included) and reports FAILED, and the next
    DELETE re-arms the deterministic anchor and converges: every stage treats
    an already-absent target as success with evidence. The addon record is
    NOT unrecorded here - it is the durable cleanup identity until the run
    succeeds; run_complete's atomic by-project sweep removes it together with
    the schedule rows, then reports REMOVED.
    """
    import os

    # This instruction only ever tears down. The hub renders DESTROY=True into
    # a destroy run's environment (the worker's isDestroyRun flag; the same
    # flag openci_tf_install's jobs key off), and the resource-order role is
    # picked from METHOD at build time (config0_stack_runtime
    # _default_resource_role: destroy -> resource/remove/execgroup, which the
    # worker routes to `config0 resource remove` -> the execgroup runs with
    # METHOD=destroy and its destroy evidence is verified). `stack run` sets
    # METHOD=create for the instruction load, so the destroy instruction
    # declares its own method here - and refuses to build under anything but a
    # destroy run (a normal dispatch of this stack would emit CREATE orders).
    if os.environ.get("DESTROY", "").lower() not in ("true", "1"):
        raise ValueError(
            "openci_tf_destroy is the openci-tf add-on's destroy instruction and "
            "runs only under a destroy run (DESTROY=True in the run environment)"
        )
    os.environ["METHOD"] = "destroy"

    stack = newStack(stackargs)

    # The install's persistent argument base (the same required keys as
    # openci_tf_install; saas-api overlays the removal workflow_id /
    # attempt_id / owner_id).
    stack.parse.add_required(key="repo", types="str")
    stack.parse.add_required(key="ghcr_image", types="str")
    stack.parse.add_required(key="image_tag", types="str")
    stack.parse.add_required(key="workflow_id", types="str")
    stack.parse.add_required(key="attempt_id", types="str")
    stack.parse.add_required(key="owner_id", types="str")
    stack.parse.add_required(key="account_alias", types="str")
    stack.parse.add_required(key="api_caller_role_arns", types="str")

    stack.parse.add_optional(key="engine_name", default="config0-xe", types="str")
    stack.parse.add_optional(key="remote_stateful_bucket", default=None, types="str")
    stack.parse.add_optional(key="openci_tf_project", default="openci-tf", types="str")
    stack.parse.add_optional(key="install_name", default="main", types="str")
    stack.parse.add_optional(key="aws_default_region", default="ap-northeast-1", types="str")
    stack.parse.add_optional(key="trigger_id", default=None, types="str")
    stack.parse.add_optional(key="openci_tf_repo_url",
                             default="https://github.com/config0-hub/openci-tf.git",
                             types="str")
    stack.parse.add_optional(
        key="openci_tf_git_ref",
        default="295b9371faed02486b3eaa8134f2104369902d44",
        types="str",
    )
    stack.parse.add_optional(key="compute_type", types="str", default="BUILD_GENERAL1_SMALL")
    stack.parse.add_optional(key="build_timeout", types="int", default=1200)
    stack.parse.add_optional(key="tofu_version", types="str", default="1.12.6")
    stack.parse.add_optional(key="cloud_tags_hash", default='null')
    stack.parse.add_optional(key="share_dir", default="/var/tmp/share")

    stack.add_execgroup("config0-hub:::aws::openci-tf-addon", "addon_execgroup")
    stack.add_execgroup("config0-hub:::aws::openci-tf-image-copy", "image_copy_execgroup")
    stack.add_execgroup("config0-hub:::aws::openci-tf-addon-tofu", "tofu_execgroup")

    stack.init_variables()
    stack.init_execgroups()
    stack.verify_variables()
    _init_common(stack)

    _insert_stage(stack, "register", 1200,
                  "openci-tf addon: close pipeline PRs and remove registration")
    _insert_tofu_stage(stack, "deploy", 2400,
                       "openci-tf addon: destroy deploy and foundation")
    _insert_image_copy(stack)
    _insert_tofu_stage(stack, "ecr", 900,
                       "openci-tf addon: destroy the ECR repository")
    _insert_stage(stack, "token", 900,
                  "openci-tf addon: delete the clone token from SSM")

    return stack.get_results()

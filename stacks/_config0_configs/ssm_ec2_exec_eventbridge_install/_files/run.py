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


# The worker's async done-marker watch is capped at 900s and only ever TIGHTENS
# (config0-worker internal/consumer/consumer.go:19-22, defaultEngineWatchTimeout
# / engineWatchTimeout). The watch starts at FIRE, but CodeBuild's own runtime
# clock starts only after queue + provisioning, so a build allowed to use the
# full 900s finishes AFTER the watch has given up: the order is requeued while
# CodeBuild is still legitimately building — a duplicate build, not a timeout.
#
# Subtract a 300s provisioning budget for CodeBuild queue + provisioning.
# Raising this ceiling means carrying the delegated
# deadline into the parking contract — an engine-contract change, recorded in
# engine-run-cycle-contract.md and deliberately not smuggled in here.
ENGINE_WATCH_CEILING = 900
PROVISIONING_HEADROOM = 300
MAX_BUILD_TIMEOUT = ENGINE_WATCH_CEILING - PROVISIONING_HEADROOM


def check_build_timeout(build_timeout):
    """Refuse a build that could outlive the worker's done-marker watch."""
    if int(build_timeout) > MAX_BUILD_TIMEOUT:
        raise ValueError(
            f"build_timeout={build_timeout} exceeds the {MAX_BUILD_TIMEOUT}s maximum: "
            f"the {ENGINE_WATCH_CEILING}s engine watch ceiling (config0-worker "
            f"internal/consumer/consumer.go defaultEngineWatchTimeout) minus "
            f"{PROVISIONING_HEADROOM}s of CodeBuild queue/provisioning headroom. "
            "The order would be requeued mid-build, producing a duplicate build. "
            "Lower build_timeout, or change the parking contract to carry the "
            "delegated deadline."
        )


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


def run(stackargs):

    import json
    import os

    # instantiate authoring stack
    stack = newStack(stackargs)

    # aws_region matches the vendored terraform's variable.aws_region
    stack.parse.add_optional(key="aws_region",
                             default="ap-northeast-1",
                             tags="tfvar",
                             types="str")

    # The dedicated Lambda-artifacts bucket is a SEPARATE stack
    # (aws_s3_bucket, resource_type cloud_storage). The config0.yaml supplies
    # its name here as a selector expression; this run.py treats it as a plain
    # input var and feeds it to both the CodeBuild upload and the terraform.
    stack.parse.add_required(key="s3_bucket",
                             tags="tfvar",
                             types="str")

    # codebuild framing (aws-lambda-python-codebuild optionals)
    stack.parse.add_optional(key="runtime",
                             default="python3.12",
                             types="str")

    stack.parse.add_optional(key="compute_type",
                             types="str",
                             default="BUILD_GENERAL1_SMALL")

    stack.parse.add_optional(key="image_type",
                             types="str",
                             default="LINUX_CONTAINER")

    stack.parse.add_optional(key="build_timeout",
                             types="int",
                             default=600)  # = MAX_BUILD_TIMEOUT (900s watch - 300s provisioning);
                                           # MUST stay a literal: stack introspection reconstructs
                                           # declaration lines only, so a module constant here
                                           # resolves to a mock and breaks the scan

    stack.parse.add_optional(key="codebuild_role",
                             default="config0-assume-poweruser")

    stack.parse.add_optional(key="cloud_tags_hash",
                             default='null')

    stack.parse.add_optional(key="stateful_id",
                             default="_random")

    stack.parse.add_optional(key="execution_id",
                             default=None)  # None registers the key unset; the legacy "null"
                                            # string is TRUTHY in the rewrite, so the
                                            # if-not-execution_id resolution below never fired
                                            # and the buildspec baked executions/null/done

    stack.parse.add_optional(key="share_dir",
                             default="/var/tmp/share")

    stack.parse.add_optional(key="script_name",
                             default="docker-to-lambda.sh")  # script name to run in codebuild

    # declare execution groups
    stack.add_execgroup("config0-hub:::aws::ssm_ec2_exec_eventbridge_lambda_build",
                        "lambda_build")

    stack.add_execgroup("config0-hub:::aws::ssm_ec2_exec_eventbridge_install",
                        "tf_execgroup")

    # add substack
    stack.add_substack('config0-hub:::config0_core::tf_executor')

    # initialize
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

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

    check_build_timeout(stack.build_timeout)

    # The order's timeout drives the target-account session the worker mints
    # (config0-worker internal/consumer/executor.go targetCredsDuration:
    # max(900, min(order_timeout, engine_timeout, 3600))). Ask for the build's
    # own timeout plus headroom, clamped to the 3600s role-chaining ceiling.
    order_timeout = min(3600, int(stack.build_timeout) + 600)

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
                       resource_name="ssm_ec2_exec_eventbridge",
                       resource_type="ssm_ec2_exec_eventbridge_install")

    tf.include(values={
        "aws_region": stack.aws_region,
        "s3_bucket": stack.s3_bucket,
        "s3_key_starter": f"{key_prefix}starter.zip",
        "s3_key_callback": f"{key_prefix}callback.zip",
        "s3_key_fallback": f"{key_prefix}fallback.zip"
    })

    # resource output to show on saas ui
    tf.output(keys=["state_machine_arn",
                    "bucket_name",
                    "instance_profile_name",
                    "dynamodb_table_name"])

    # finalize the tf_executor
    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()

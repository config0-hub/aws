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

# ref 4353253452354
def _get_buildspec_hash(stack):

    contents_1 = f'''version: 0.2
phases:
  install:
    on-failure: CONTINUE
    commands:
      - echo "Installing system dependencies..."
      - apt-get update && apt-get install -y zip

  pre_build:
    on-failure: CONTINUE
    commands:
      - aws s3 cp s3://$UPLOAD_BUCKET/{stack.stateful_id}/state/src.{stack.stateful_id}.zip /tmp/{stack.stateful_id}.zip --quiet
      - mkdir -p {stack.share_dir}
      - mkdir -p {stack.run_share_dir}
      - unzip -o /tmp/{stack.stateful_id}.zip -d {stack.run_share_dir}/
      - rm -rf /tmp/{stack.stateful_id}.zip 
'''

    contents_3 = f'''
  build:
    commands:
      - cd {stack.run_share_dir}/
      - chmod 755 {stack.script_name}
      - ./{stack.script_name}
      
  post_build:
    commands:
      - date +%s > done
      - echo "Uploading done to S3 bucket..."
      - aws s3 cp done s3://{stack.tmp_bucket}/executions/{stack.execution_id}/done
'''
 
    contents = contents_1 + contents_3

    return stack.b64_encode(contents)


def run(stackargs):

    import json
    import os

    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_required(key="config0_lambda_execgroup_name")
    stack.parse.add_required(key="lambda_name")
    stack.parse.add_required(key="s3_bucket")

    stack.parse.add_optional(key="handler",
                             default="app.handler")

    stack.parse.add_optional(key="runtime",
                             default="python3.8")

    stack.parse.add_optional(key="memory_size",
                             default="256")

    stack.parse.add_optional(key="lambda_timeout",
                             default="900")

    stack.parse.add_optional(key="lambda_layers")
    stack.parse.add_optional(key="policy_template_hash")

    stack.parse.add_optional(key="aws_default_region",
                             default="us-east-1")

    stack.parse.add_optional(key="lambda_env_vars_hash")

    stack.parse.add_optional(key="cloud_tags_hash",
                             default='null')

    stack.parse.add_optional(key="stateful_id",
                             default="_random")

    stack.parse.add_optional(key="execution_id",
                             default="null")

    stack.parse.add_optional(key="share_dir",
                             default="/var/tmp/share")

    stack.parse.add_optional(key="script_name",
                             default="docker-to-lambda.sh")  # script name to run in codebuild

    stack.parse.add_optional(key="codebuild_role",
                             default="config0-assume-poweruser")

    stack.parse.add_optional(key="compute_type",
                             types="str",
                             default="BUILD_GENERAL1_SMALL")

    stack.parse.add_optional(key="image_type",
                             types="str",
                             default="LINUX_CONTAINER")

    stack.parse.add_optional(key="build_timeout",
                             types="int",
                             default=900)

    # declare execution groups
    stack.add_execgroup("config0-publish:::aws::py_to_lambda-codebuild",
                        "py_to_lambda")

    # add substack
    stack.add_substack('config0-publish:::aws_lambda')

    # initialize variables
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    # ref 5490734650346
    stack.add_execgroup(f"{stack.config0_lambda_execgroup_name} {stack.py_to_lambda.name}",
                        "buildgroups",
                        overide=True)

    if not stack.execution_id and os.environ.get("EXECUTION_ID"):
        stack.set_variable("execution_id", os.environ["EXECUTION_ID"])
    elif not stack.execution_id:
        stack.set_variable("execution_id", stack.stateful_id)

    # reset exec groups
    stack.reset_execgroups()

    _set_codebuild_image(stack)

    # set more stack vars
    stack.set_variable("run_share_dir",
                       os.path.join(stack.share_dir,
                       stack.stateful_id))

    # create lambda zip file
    build_envs = {
        'DOCKER_TEMP_IMAGE': f'{stack.lambda_name}-temp',
        'LAMBDA_PKG_NAME': stack.lambda_name,
        'LAMBDA_PKG_DIR': "/var/tmp/package/lambda",
        'PYTHON_VERSION': stack.runtime.split("python")[1],
        'S3_BUCKET': stack.s3_bucket,
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
        'BUILDSPEC_HASH': _get_buildspec_hash(stack),
        'BUILD_TIMEOUT': stack.build_timeout,
        'USE_CODEBUILD': "True",
        "AWS_DEFAULT_REGION": stack.aws_default_region
    }

    # we need to declare app initially - lambda app
    env_vars = {
        'CODEBUILD_PARAMS_HASH': stack.b64_encode({
            "env_vars": build_envs,
            "build_env_vars": build_envs}
        ),
        'CHROOTFILES_DEST_DIR': stack.run_share_dir,
        "AWS_DEFAULT_REGION": stack.aws_default_region,
        'WORKING_DIR': stack.run_share_dir,
        'APP_NAME': "lambda",
        'APP_DIR': "var/tmp/lambda"
    }

    inputargs = {
        "name": stack.lambda_name,
        "env_vars": json.dumps(env_vars)
    }

    if stack.cloud_tags_hash:
        inputargs["cloud_tags_hash"] = stack.cloud_tags_hash

    inputargs["use_docker"] = "True"

    stack.buildgroups.insert(**inputargs)

    # create lambda function
    arguments = {
        "s3_key": f"{stack.lambda_name}.zip",
        "lambda_name": stack.lambda_name,
        "s3_bucket": stack.s3_bucket,
        "handler": stack.handler,
        "runtime": stack.runtime,
        "memory_size": stack.memory_size,
        "lambda_timeout": stack.lambda_timeout,
        "aws_default_region": stack.aws_default_region
    }

    if stack.get_attr("policy_template_hash"):
        arguments["policy_template_hash"] = stack.policy_template_hash

    if stack.get_attr("lambda_layers"):
        arguments["lambda_layers"] = stack.lambda_layers

    if stack.get_attr("lambda_env_vars_hash"):
        arguments["lambda_env_vars_hash"] = stack.lambda_env_vars_hash

    if stack.cloud_tags_hash:
        arguments["cloud_tags_hash"] = stack.cloud_tags_hash

    if stack.get_attr("stateful_id"):
        arguments["stateful_id"] = stack.stateful_id

    inputargs = {
        "arguments": arguments,
        "automation_phase": "infrastructure",
        "human_description": f'Create lambda function for {stack.lambda_name}'
    }

    stack.aws_lambda.insert(display=True,
                            **inputargs)

    return stack.get_results()

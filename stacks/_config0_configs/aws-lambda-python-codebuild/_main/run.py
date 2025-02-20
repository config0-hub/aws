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
def _get_buildspec_hash_v1(stack):

    contents_1 = '''version: 0.2
phases:
  install:
    on-failure: ABORT
    commands:
      - echo "Installing system dependencies..."
      - apt-get update && apt-get install -y zip

  pre_build:
    on-failure: ABORT
    commands:
      - aws s3 cp s3://{tmp_bucket}/{stateful_id}/state/src.{stateful_id}.zip {tmpdir}/{stateful_id}.zip --quiet
      - mkdir -p {run_share_dir}
      - unzip -o {tmpdir}/{stateful_id}.zip -d {run_share_dir}/
      - rm -rf {tmpdir}/{stateful_id}.zip 
      - echo "Creating a virtual environment..."
      - cd {run_share_dir}/ && python3 -m venv venv
'''.format(tmpdir="/tmp",
           run_share_dir=stack.run_share_dir,
           tmp_bucket=stack.tmp_bucket,
           stateful_id=stack.stateful_id)

    contents_2 = '''      - export PYTHON_VERSION=`python -c "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')"`
'''

    contents_3 = '''
  build:
    on-failure: ABORT
    commands:
      - cd {run_share_dir}/
      - . venv/bin/activate
      - echo "Installing project dependencies..."
      - pip install -r src/requirements.txt
      - cp -rp src/* venv/lib/python$PYTHON_VERSION/site-packages/

  post_build:
    commands:
      - cd {run_share_dir}/
      - cd venv/lib/python$PYTHON_VERSION/site-packages/
      - zip -q -r /tmp/{lambda_name}.zip .
      - aws s3 cp /tmp/{lambda_name}.zip s3://{tmp_bucket}/{stateful_id}/state/src.{stateful_id}.zip --quiet

'''.format(run_share_dir=stack.run_share_dir,
           s3_bucket=stack.s3_bucket,
           stateful_id=stack.stateful_id,
           lambda_name=stack.lambda_name)
 
    contents = contents_1 + contents_2 + contents_3

    return stack.b64_encode(contents)

# ref 4353253452354
def _get_buildspec_hash_v2(stack):

    contents_1 = '''version: 0.2
phases:
  install:
    on-failure: ABORT
    commands:
      - echo "Installing system dependencies..."
      - apt-get update && apt-get install -y zip

  pre_build:
    on-failure: ABORT
    commands:
      - aws s3 cp s3://{tmp_bucket}/{stateful_id}/state/src.{stateful_id}.zip {tmpdir}/{stateful_id}.zip --quiet
      - mkdir -p {share_dir}
      - mkdir -p {run_share_dir}
      - unzip -o {tmpdir}/{stateful_id}.zip -d {run_share_dir}/
      - rm -rf {tmpdir}/{stateful_id}.zip 
'''.format(tmpdir="/tmp",
           share_dir=stack.share_dir,
           run_share_dir=stack.run_share_dir,
           tmp_bucket=stack.tmp_bucket,
           stateful_id=stack.stateful_id)

    contents_3 = '''
  build:
    on-failure: ABORT
    commands:
      - cd {run_share_dir}/
      - chmod 755 {script_name}
      - ./{script_name}

'''.format(run_share_dir=stack.run_share_dir,
           script_name=stack.script_name)
 
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

    # reset exec groups
    stack.reset_execgroups()

    _set_codebuild_image(stack)

    # set more stack vars
    stack.set_variable("run_share_dir",
                       os.path.join(stack.share_dir,
                       stack.stateful_id))

    # create lambda zip file
    _env_vars = {
        'DOCKER_TEMP_IMAGE': f'{stack.lambda_name}-temp',
        'LAMBDA_PKG_NAME': stack.lambda_name,
        'LAMBDA_PKG_DIR': "/var/tmp/package/lambda",
        'PYTHON_VERSION': stack.runtime.split("python")[1],
        'S3_BUCKET': stack.s3_bucket,
        'STATEFUL_ID': stack.stateful_id,
        'TMP_BUCKET': stack.tmp_bucket,
        'SHARE_DIR': stack.share_dir,
        'WORKING_SUBDIR':'var/tmp/lambda',
        'RUN_SHARE_DIR': stack.run_share_dir,
        'CHROOTFILES_DEST_DIR': stack.run_share_dir,
        'WORKING_DIR': stack.run_share_dir,
        'BUILD_IMAGE': stack.build_image,
        'CODEBUILD_COMPUTE_TYPE': stack.compute_type,
        'BUILDSPEC_HASH': _get_buildspec_hash_v2(stack),
        'BUILD_TIMEOUT': stack.build_timeout,
        "AWS_DEFAULT_REGION": stack.aws_default_region
    }

    # we need to declare app initially - lambda app
    env_vars = {
        'CODEBUILD_PARAMS_HASH': stack.b64_encode( {
            "env_vars": _env_vars,
            "build_env_vars":_env_vars}
        ),
        'CHROOTFILES_DEST_DIR': stack.run_share_dir,
        "AWS_DEFAULT_REGION": stack.aws_default_region,
        'WORKING_DIR': stack.run_share_dir,
        'APP_NAME':"lambda",
        'APP_DIR':"var/tmp/lambda"
    }

    inputargs = {
        "name": stack.lambda_name,
        "env_vars": json.dumps(env_vars)
    }

    if stack.cloud_tags_hash:
        inputargs["cloud_tags_hash"] = stack.cloud_tags_hash

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

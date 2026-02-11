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


class _BuildSpecs(object):

    def __init__(self, stack):
        self.classname = '_BuildSpecs'
        self.stack = stack
        self._init_buildspecs()

    def _init_buildspecs(self):
        try:
            self.ssm_params = self.stack.b64_decode(self.stack.ssm_params_hash)
        except Exception:
            self.ssm_params = {}

        try:
            self.prebuild = self.stack.b64_decode(self.stack.prebuild_hash)
        except Exception:
            self.prebuild = self._default_prebuild()

        if self.stack.get_attr("build_hash"):
            self.build = self.stack.b64_decode(self.stack.build_hash)
        elif self.stack.get_attr("docker_registry") == "ecr":
            self.build = self._default_docker_ecr()
        elif self.stack.get_attr("docker_registry") == "dockerhub":
            self.build = self._default_dockerhub()

        try:
            self.postbuild = self.stack.b64_decode(self.stack.postbuild_hash)
        except Exception:
            self.postbuild = self._default_postbuild()

    def _add_build_lines(self, lines):
        for line in lines:
            self.contents = self.contents + ' '*7 + f'- {line}'
            self.contents = self.contents + "\n"

    def _default_base(self):
        self.contents = '''
version: 0.2
env:
  variables:
    code_dir: /tmp/code/src
    AWS_DEFAULT_REGION: ${aws_default_region}
    AWS_ACCOUNT_ID: ${aws_account_id}
    S3_BUCKET: ${s3_bucket}
'''
        if not self.ssm_params:
            return

        self.contents = self.contents + ' '*2 + 'parameter-store:'
        self.contents = self.contents + "\n"

        for key, value in self.ssm_params.items():
            self.contents = self.contents + ' '*4 + f'{key}: {value}'
            self.contents = self.contents + "\n"

        self.contents = self.contents + 'phases:'

    @staticmethod
    def _default_prebuild_headers():
        contents = '''
  pre_build:
    on-failure: CONTINUE
    commands:   
'''
        return contents

    def _default_prebuild(self):
        lines = []

        if self.ssm_params.get("DOCKER_TOKEN") and self.ssm_params.get("DOCKER_USERNAME"):
            lines.append(
                'echo $DOCKER_TOKEN | docker login --username $DOCKER_USERNAME --password-stdin')

        if self.stack.get_attr("docker_registry") == "ecr":
            lines.append('aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com')

        lines.append(
            'export COMMIT_HASH=$${COMMIT_HASH:=$CODEBUILD_RESOLVED_SOURCE_VERSION}')
        lines.append('mkdir -p ~/.ssh')
        lines.append('echo $SSH_KEY | base64 -d > ~/.ssh/id_rsa')
        lines.append('chmod 600 ~/.ssh/id_rsa')
        lines.append('eval "$(ssh-agent -s)"')
        lines.append('mkdir -p $code_dir')
        lines.append('cd $code_dir')
        lines.append('git init')
        lines.append('git remote add origin $GIT_URL')
        lines.append('git fetch --quiet origin ')
        lines.append('git checkout --quiet -f $COMMIT_HASH')
        lines.append('rm -rf .git')

        return lines

    @staticmethod
    def _default_build_headers():
        contents = '''
  build:
    commands:   
'''
        return contents

    @staticmethod
    def _default_dockerhub():
        lines = ['docker build -t docker.io/$DOCKER_USERNAME/$DOCKER_REPO_NAME:$COMMIT_HASH . -f Dockerfile',
                 'docker tag docker.io/$DOCKER_USER/$DOCKER_REPO_NAME:$COMMIT_HASH docker.io/$DOCKER_USER/$DOCKER_REPO_NAME:latest',
                 'docker push docker.io/$DOCKER_USER/$DOCKER_REPO_NAME --all-tags']

        return lines

    @staticmethod
    def _default_docker_ecr():
        lines = [
            'docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$DOCKER_REPO_NAME:$COMMIT_HASH . -f Dockerfile',
            'docker tag $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$DOCKER_REPO_NAME:$COMMIT_HASH $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$DOCKER_REPO_NAME:latest',
            'docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$DOCKER_REPO_NAME --all-tags']

        return lines

    @staticmethod
    def _default_postbuild_headers():
        contents = '''
  post_build:
    commands:
'''
        return contents

    @staticmethod
    def _default_postbuild():
        lines = [
            'echo "export CODEBUILD_BUILD_ARN=$CODEBUILD_BUILD_ARN" > /tmp/codebuild.env ; echo "export CODEBUILD_BUILD_ID=$CODEBUILD_BUILD_ID" >> /tmp/codebuild.env ; echo "export CODEBUILD_BUILD_NUMBER=$CODEBUILD_BUILD_NUMBER" >> /tmp/codebuild.env',
            'echo "" ; cat /tmp/codebuild.env ; echo ""']

        return lines

    def _insert_prebuild(self):
        self.contents = self.contents + self._default_prebuild_headers()
        return self._add_build_lines(self.prebuild)

    def _insert_build(self):
        self.contents = self.contents + self._default_build_headers()
        return self._add_build_lines(self.build)

    def _insert_postbuild(self):
        self.contents = self.contents + self._default_postbuild_headers()
        return self._add_build_lines(self.postbuild)

    def get(self):
        self._default_base()
        self._insert_prebuild()
        self._insert_build()
        self._insert_postbuild()

        return self.contents


def run(stackargs):
    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_required(key="s3_bucket",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_required(key="s3_bucket_cache",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_required(key="s3_bucket_output",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_required(key="codebuild_name",
                             tags="tfvar,db",
                             types="str")

    # hashes that needed to be convered by _BuildSpec class
    stack.parse.add_optional(key="image_type",
                             default='LINUX_CONTAINER',
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="build_image",
                             default='aws/codebuild/standard:5.0',
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="build_timeout",
                             default='444',
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="compute_type",
                             default='BUILD_GENERAL1_SMALL',
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_optional(key="privileged_mode",
                             choices=["true", "false"],
                             default='true',
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="codebuild_env_vars_hash",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="description",
                             tags="tfvar",
                             types="str")  # testtest777

    stack.parse.add_optional(key="buildspec_hash",
                             tags="tfvar",
                             types="str")

    stack.parse.add_optional(key="prebuild_hash",
                             types="str")

    stack.parse.add_optional(key="build_hash",
                             types="str")

    stack.parse.add_optional(key="postbuild_hash",
                             types="str")

    stack.parse.add_optional(key="ssm_params_hash",
                             types="str")

    stack.parse.add_optional(key="docker_registry",
                             types="str")

    stack.parse.add_optional(key="aws_default_region",
                             default="eu-west-1",
                             tags="tfvar,resource,db,tf_exec_env",
                             types="str")

    stack.parse.add_optional(key="subnet_ids",
                             default="null")

    stack.parse.add_optional(key="vpc_id",
                             default="null",
                             tags="tfvar,db",
                             types="str")

    stack.parse.add_required(key="security_group_id",
                             default="null",
                             tags="tfvar,db",
                             types="str")

    # Add execgroup
    stack.add_execgroup("config0-publish:::aws::codebuild",
                        "tf_execgroup")

    # Add substack
    stack.add_substack('config0-publish:::tf_executor')

    # Initialize Variables in stack
    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    if not stack.get_attr("buildspec_hash"):
        _buildspec = _BuildSpecs(stack)
        stack.set_variable("buildspec_hash",
                           stack.b64_encode(_buildspec.get()),
                           tags="tfvar",
                           types="str")

    if stack.get_attr("subnet_ids"):
        stack.set_variable("subnet_ids",
                           sorted(stack.to_list(stack.subnet_ids)),
                           tags="tfvar",
                           types="list")

    if stack.get_attr("security_group_id"):
        stack.set_variable("security_group_ids",
                           [stack.security_group_id],
                           tags="tfvar",
                           types="list")

    if stack.get_attr("codebuild_env_vars_hash"):
        stack.set_variable("codebuild_env_vars",
                           stack.b64_decode(stack.codebuild_env_vars_hash),
                           tags="tfvar",
                           types="dict")

    if not stack.get_attr("description"):
        stack.set_variable("description",
                           f"Codebuild project {stack.codebuild_name}",
                           tags="tfvar",
                           types="str")

    stack.set_variable("timeout", 1800)

    # use the terraform constructor
    tf = TFConstructor(stack=stack,
                       provider="aws",
                       execgroup_name=stack.tf_execgroup.name,
                       resource_name=stack.codebuild_name,
                       resource_type="aws_codebuild")

    tf.include(values={
        "aws_default_region": stack.aws_default_region,
        "name": stack.codebuild_name,
        "codebuild_project_name": stack.codebuild_name
    })

    tf.output(keys=["service_role",
                    "environment",
                    "arn"])

    # finalize the tf_executor
    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()
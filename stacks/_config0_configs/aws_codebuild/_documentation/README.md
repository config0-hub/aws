**Description**

  - The stack setups up codebuild.

**Required**

| argument           | description                            | var type |  default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| s3_bucket   | s3 bucket for codebuild               | string   |        |
| s3_bucket_cache   | s3 bucket for codebuild cache (docker related)               | string   |        |
| codebuild_name   | codebuild name for the project               | string   |        |

**Optional**

| argument           | description                            | var type |  default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| aws_default_region   | default aws region               | string   | us-east-1         |
| buildspec_hash | buildspec for codebuild as base64 hash | string   | None         |
| prebuild_hash | prebuild stage for codebuild as base64 hash | string   | None         |
| build_hash | build stage for codebuild as base64 hash | string   | None         |
| postbuild_hash | postbuild stage for codebuild as base64 hash | string   | None         |
| codebuild_env_vars_hash | the environmental variables for codebuild as base64 | string  | None         |
| cloud_tags_hash | the tags for the resources in the cloud as base64 | string  | None         |
| ssm_params_hash | ssm parameters to inserted (already uploaded) as base64 | string  | None         |
| description   | description for the project               | string   |        |
| privileged_mode   | privileged_mode for the docker builds               | string   |  true      |
| image_type   | image_type for codebuild project               | string   |  LINUX_CONTAINER      |
| build_image   | build_image for codebuild project               | string   |  aws/codebuild/standard:5.0      |
| build_timeout   | build_timeout for codebuild project               | string   |  5  |
| compute_type   | compute_type for codebuild project               | string   |  BUILD_GENERAL1_SMALL  |
| docker_registry   | docker_registry to upload images | string   |  None(ecr)  |
| publish_to_saas   | publish codebuild project to the UI | boolean   |  None  |

**Sample entry**

```
labels:
   general: 
     environment: dev
     purpose: ci
infrastructure:
   codebuild:
       stack_name: config0-hub:::aws_codebuild
       arguments:
          aws_default_region: eu-west-1
          s3_bucket: flask-sample-private-codebuild-ci
          s3_bucket_cache: flask-sample-private-codebuild-cache
          codebuild_name: flask-sample-private
          docker_registry: ecr
          ssm_params_hash:
            SSH_KEY: /codebuild/flask-sample-private/sshkeys/private
          codebuild_env_vars_hash:
            GIT_URL: git@github.com:williaumwu/flask_sample-private.git
            DOCKER_REPO_NAME: flask_sample
          cloud_tags_hash:
            billing_reference: flask-sample
            environmental: dev
            phase: ci
       to_base64:
         - cloud_tags_hash
         - codebuild_env_vars_hash
         - ssm_params_hash
       credentials:
         - reference: eval-config0-iam
           orchestration: true
       inputvars:
         - reference: github-token
           orchestration: true
       labels:
          - general
```

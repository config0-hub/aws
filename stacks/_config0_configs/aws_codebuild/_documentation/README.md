# AWS CodeBuild

## Description
This stack creates and configures an AWS CodeBuild project with customizable environment settings, build specifications, and integration with various Docker registries. It handles the generation of buildspec files and sets up the necessary infrastructure for CI/CD pipelines within AWS.

## Variables

### Required Variables

| Name | Description | Default |
|------|-------------|---------|
| s3_bucket | S3 bucket name | |
| s3_bucket_cache | S3 bucket name for caching | |
| s3_bucket_output | S3 bucket name for outputs | |
| codebuild_name | CodeBuild project name | |
| security_group_id | Security group ID | null |

### Optional Variables

| Name | Description | Default |
|------|-------------|---------|
| image_type | Configuration for image type | LINUX_CONTAINER |
| build_image | Configuration for build image | aws/codebuild/standard:5.0 |
| build_timeout | Configuration for build timeout | 444 |
| compute_type | Configuration for compute type | BUILD_GENERAL1_SMALL |
| privileged_mode | Configuration for privileged mode (choices: true, false) | true |
| codebuild_env_vars_hash | Environment variables for CodeBuild in base64 format | |
| description | Configuration for description | |
| buildspec_hash | Buildspec configuration in base64 format | |
| prebuild_hash | Pre-build commands in base64 format | |
| build_hash | Build commands in base64 format | |
| postbuild_hash | Post-build commands in base64 format | |
| ssm_params_hash | SSM parameters in base64 format | |
| docker_registry | Docker registry URL | |
| aws_default_region | Default AWS region | eu-west-1 |
| subnet_ids | Subnet ID list | null |
| vpc_id | VPC network identifier | null |

## Features
- Supports multiple Docker registry types (ECR, DockerHub)
- Automatically generates buildspec.yml files if not provided
- Custom build, pre-build, and post-build phases
- Integration with AWS Parameter Store (SSM)
- VPC configuration support for network-isolated builds
- Environment variable management for build processes

## Dependencies

### Substacks
- [config0-publish:::tf_executor](https://api-app.config0.com/web_api/v1.0/stacks/config0-publish/tf_executor)

### Execgroups
- [config0-publish:::aws::codebuild](https://api-app.config0.com/web_api/v1.0/exec/groups/config0-publish/aws/codebuild)

## License
Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
# AWS CodeBuild Project Module

This module provisions an AWS CodeBuild project with associated IAM roles and permissions, optimized for CI/CD pipelines.

## Features

- Creates a CodeBuild project with configurable build specifications
- Sets up necessary IAM roles and policies
- Configures S3 buckets for artifacts, logs, and cache
- Supports VPC networking configuration
- Customizable environment variables and build environment settings

## Usage

```hcl
module "codebuild" {
  source = "path/to/module"

  codebuild_name    = "my-project-build"
  s3_bucket         = "my-build-artifacts-bucket"
  s3_bucket_output  = "my-build-output-bucket"
  s3_bucket_cache   = "my-build-cache-bucket"
  buildspec_hash    = base64encode(file("${path.module}/buildspec.yml"))
  
  # Optional configurations
  build_timeout     = "15"
  build_image       = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
  compute_type      = "BUILD_GENERAL1_MEDIUM"
  
  codebuild_env_vars = {
    ENVIRONMENT = "dev"
    DEBUG       = "true"
  }
  
  # VPC configuration (optional)
  vpc_id              = "vpc-12345678"
  subnet_ids          = ["subnet-12345678", "subnet-87654321"]
  security_group_ids  = ["sg-12345678"]
  
  cloud_tags = {
    Environment = "Development"
    Project     = "MyApp"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| aws_default_region | The AWS region where resources will be created | string | "eu-west-1" | no |
| build_image | The Docker image to use for the CodeBuild project | string | "aws/codebuild/standard:5.0" | no |
| image_type | The type of build environment to use for related builds | string | "LINUX_CONTAINER" | no |
| s3_bucket | The S3 bucket where build artifacts and logs will be stored | string | n/a | yes |
| s3_bucket_output | The S3 bucket where build output artifacts will be stored | string | n/a | yes |
| s3_bucket_cache | The S3 bucket where build cache will be stored | string | n/a | yes |
| cloud_tags | Additional tags as a map to apply to all resources | map(string) | {} | no |
| codebuild_name | The name of the CodeBuild project | string | n/a | yes |
| codebuild_env_vars | Environmental variables for the CodeBuild project | map(string) | {} | no |
| privileged_mode | Whether to enable running the Docker daemon inside a Docker container | bool | true | no |
| description | Description of the CodeBuild project | string | "Codebuild project" | no |
| build_timeout | Number of minutes, from 5 to 480 (8 hours), for AWS CodeBuild to wait until timing out any build | string | "5" | no |
| compute_type | Compute resources the build project will use | string | "BUILD_GENERAL1_SMALL" | no |
| buildspec_hash | Buildspec template as a base64 hash | string | n/a | yes |
| vpc_id | The VPC ID where the CodeBuild project will run | string | null | no |
| subnet_ids | The subnet IDs where the CodeBuild project will run | list(string) | null | no |
| security_group_ids | The security group IDs to apply to the CodeBuild project | list(string) | null | no |

## Outputs

| Name | Description |
|------|-------------|
| service_role | The ARN of the IAM service role created for the CodeBuild project |
| environment | The environment configuration of the CodeBuild project |
| arn | The ARN of the CodeBuild project |

## Notes

- Make sure your buildspec.yml is properly formatted according to [AWS documentation](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html)
- The IAM role created has permissions for logs, EC2, ECR, SNS, SSM, and S3 operations
- VPC configuration is optional but required if you need to access resources in a VPC

## License

Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
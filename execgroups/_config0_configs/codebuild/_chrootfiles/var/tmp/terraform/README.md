# AWS CodeBuild project (execgroup `codebuild`)

Makes one CodeBuild project for the CodeBuild CI family (Linear CON-101) through the
community module `cloudposse/codebuild/aws`, pinned to `2.0.2`. The module makes the
project, its IAM service role and the role's policies. The project has `NO_SOURCE`, and
the CI's `trigger-codebuild` Lambda passes no source at `start_build` either, so every
build starts in an empty workspace. The inline buildspec (rendered by the `aws_codebuild`
stack and passed base64-encoded as `buildspec_hash`) clones the repository itself in
`pre_build`: it writes the deploy key to `~/.ssh/id_rsa` (CodeBuild pulls it from the
buildspec's `parameter-store` entry `SSH_KEY`, the SSM parameter `/ec2/keypair/<key_pair_id>`
EC2 keeps for the key pair), then `git init`, `git remote add origin $GIT_URL` (a project
environment variable), `git fetch` and `git checkout -f $COMMIT_HASH`, the commit the
Lambda passes as a build environment variable. A repository that ships its own
`buildspec.yml` gets that file as the `buildspecOverride` instead, and fetching the code
is that buildspec's job.

## Why this module

Decided 2026-10-17 (research comment on CON-101). `terraform-aws-modules`, the
organisation behind the vpc and rds modules, publishes no CodeBuild module. Of the
registry's CodeBuild modules only Cloud Posse's makes every resource this execgroup
made by hand before: the IAM role and policy, a project with `source_type` and an
inline `buildspec`, an S3 cache (on a bucket the module makes; it cannot use an
existing bucket, see below), `vpc_config`, `logs_config` with both CloudWatch and S3
logs, and environment variables. `lgallard/codebuild/aws` and
`SPHTech-Platform/codebuild/aws` make the project only. Cloud Posse's repository was
last pushed 2026-02-17.

Two module behaviours are pinned down here on purpose:

- `label_value_case = "none"` so the project (and role) keep `codebuild_name` exactly
  as given; the module's label would lowercase it otherwise.
- `default_permissions_enabled = false` with `custom_policy` carrying this execgroup's
  own statements, so the module's broad default statements never apply. The module
  still adds its own cache-bucket policy for the S3 cache.
- `cache_type = "S3"` with no `s3_cache_bucket_name`: the module makes the cache bucket
  (its label plus a random suffix, `force_destroy = true`, objects expire after
  `cache_expiration_days`, 7 by default) and destroys it with the project. Given an
  existing bucket instead, the module's cache policy renders `Resource = ["", "/*"]`,
  which IAM rejects (Cloud Posse issue #148), so the project could never apply.

## Runtime

`required_version >= 1.3` and `hashicorp/aws >= 5.0` are the module's floors. No lock
file ships with this execgroup: `tofu init` resolves the provider at run time (the
2026-10-16 rule: any Terraform or OpenTofu version runs). The `aws_codebuild` stack
names `tofu:1.11.14`.

Validated 2026-10-17 with `tofu 1.11.14` and `terraform 1.11.4`, each
`init -backend=false` then `validate`.

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| aws_default_region | Region the project is created in | string | "eu-west-1" | no |
| codebuild_name | Project name; also the IAM role name | string | n/a | yes |
| description | Project description | string | "Codebuild project" | no |
| buildspec_hash | The inline buildspec, base64-encoded | string | n/a | yes |
| s3_bucket | Bucket for the S3 build logs (`<bucket>/codebuild/logs`) | string | n/a | yes |
| s3_bucket_output | Bucket the build writes its output to (role policy only) | string | n/a | yes |
| build_image | Build image | string | "aws/codebuild/standard:5.0" | no |
| image_type | Environment type | string | "LINUX_CONTAINER" | no |
| compute_type | Compute size | string | "BUILD_GENERAL1_SMALL" | no |
| privileged_mode | Docker-in-Docker | bool | true | no |
| build_timeout | Minutes, 5 to 480 | number | 5 | no |
| codebuild_env_vars | Plaintext environment variables | map(string) | {} | no |
| vpc_id, subnet_ids, security_group_ids | VPC placement; all three or none | string, list(string), list(string) | null | no |
| cloud_tags | Tags merged onto every resource | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| arn | ARN of the CodeBuild project |
| project_name | Name of the CodeBuild project |
| cache_bucket_name | Name of the S3 cache bucket the module made |
| service_role | ARN of the IAM service role |
| environment | The build environment as given: compute_type, image, type, privileged_mode |

## License

Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

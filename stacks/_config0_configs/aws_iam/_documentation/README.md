# AWS IAM Credentials Stack

## Description

This stack creates AWS IAM credentials with customizable policies. It generates IAM access keys and secrets, applying a specified policy or using default permissions for AWS services like S3, Lambda, ECR, EC2, SSM, EKS, and RDS.

## Variables

### Required

| Name | Description | Default |
|------|-------------|---------|
| iam_name | SSH key identifier for resource access | |
| policy_name | Name of the IAM policy to be created | |

### Optional

| Name | Description | Default |
|------|-------------|---------|
| aws_default_region | Default AWS region | eu-west-1 |
| policy_hash | Base64 encoded IAM policy document | |
| allows_hash | Base64 encoded list of policy allow statements | |
| denies_hash | Base64 encoded list of policy deny statements | |

## Features

- Creates IAM credentials (access key ID and secret access key)
- Allows custom IAM policy definitions
- Supports default policy creation with common AWS service permissions
- Customizable policy allow/deny statements

## Dependencies

### Substacks
- [config0-publish:::tf_executor](https://api-app.config0.com/web_api/v1.0/stacks/config0-publish/tf_executor)

### Execgroups
- [config0-publish:::aws::iam-keys](https://api-app.config0.com/web_api/v1.0/exec/groups/config0-publish/aws/iam-keys)

## License

Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
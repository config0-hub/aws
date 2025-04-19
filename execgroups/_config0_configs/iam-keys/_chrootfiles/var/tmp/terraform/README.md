# AWS IAM User Module

This module creates an IAM user with an access key and attaches a policy to it. It's designed for creating system users with specific permissions in AWS.

## Usage

```hcl
module "iam_user" {
  source = "path/to/module"

  # Optional: customize the user and policy
  iam_name    = "custom-user-name"
  policy_name = "custom-policy-name"
  policy      = "base64_encoded_policy_document"
  cloud_tags  = {
    Environment = "production"
    Project     = "infrastructure"
  }
}
```

## Requirements

| Name | Version |
|------|---------|
| opentofu | >= 1.8.0 |
| aws | >= 4.0.0 |

## Resources Created

- AWS IAM User
- AWS IAM Access Key
- AWS IAM Policy
- AWS IAM User Policy Attachment

## Input Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| policy | Base64 encoded IAM policy document | `string` | `"eyJWZXJzaW9uIjogIjIwMTItMTAtMTciLCAiU3RhdGVtZW50IjogW3siQWN0aW9uIjogWyJzMzoqIiwgImVjcjoqIiwgImVjMjoqIiwgInNzbToqIiwgImVrczoqIiwgInJkczoqIiwgImR5bmFtb2RiOioiXSwgIlJlc291cmNlIjogIioiLCAiRWZmZWN0IjogIkFsbG93In1dfQ=="` | No |
| policy_name | Name of the IAM policy to create | `string` | `"eval-config0-user"` | No |
| iam_name | Name of the IAM user to create | `string` | `"test-config0-user"` | No |
| aws_default_region | AWS region for resources | `string` | `"us-east-1"` | No |
| cloud_tags | Additional tags as a map | `map(string)` | `{}` | No |

## Outputs

The module has commented output values that can be uncommented if needed:

- `AWS_ACCESS_KEY_ID`: The access key ID for the created IAM user
- `AWS_SECRET_ACCESS_KEY`: The secret access key for the created IAM user

## Note

The default policy provides full access to S3, ECR, EC2, SSM, EKS, RDS, and DynamoDB services. Consider limiting these permissions based on the principle of least privilege for production environments.

## License

Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
# AWS IAM Role for EC2 Instances

This OpenTofu module creates an IAM role, instance profile, and associated policy for EC2 instances. The role provides necessary permissions for EC2 instances to interact with various AWS services.

## Usage

```hcl
module "ec2_iam_role" {
  source = "path/to/module"

  # Optional: customize the role and profile names
  role_name             = "custom-ec2-role"
  iam_instance_profile  = "custom-ec2-profile"
  iam_role_policy_name  = "custom-ec2-policy"
  
  # Optional: add tags
  cloud_tags = {
    Environment = "Production"
    Project     = "MyProject"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| aws_default_region | The AWS region to deploy resources to | `string` | `"us-east-1"` | no |
| role_name | Name of the IAM role to be created | `string` | `"eval-config0-ec2"` | no |
| iam_instance_profile | Name of the IAM instance profile to be created | `string` | `"eval-config0-ec2"` | no |
| iam_role_policy_name | Name of the IAM role policy to be created | `string` | `"eval-config0-ec2"` | no |
| assume_policy | Base64 encoded assume role policy document for EC2 instances | `string` | Base64 encoded policy | no |
| policy | Base64 encoded IAM policy document defining permissions for the role | `string` | Base64 encoded policy | no |
| cloud_tags | Additional tags to apply to all resources as a map | `map(string)` | `{}` | no |

## Outputs

This module doesn't expose any outputs by default.

## Policy Details

The default policy provides broad permissions to several AWS services, including:
- Amazon S3
- Amazon ECR
- Amazon EC2
- AWS Systems Manager
- Amazon EKS
- Amazon RDS
- Amazon DynamoDB

**Note:** For production use, it's recommended to restrict these permissions to the minimum necessary for your application.

## Requirements

| Name | Version |
|------|---------|
| OpenTofu | >= 1.8.8 |

## License

Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
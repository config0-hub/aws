# AWS IAM Credentials Stack

## Description

This stack creates AWS IAM credentials with customizable policies. It generates IAM access keys and secrets, applying a specified policy or using default permissions for AWS services like S3, Lambda, ECR, EC2, SSM, EKS, and RDS.

## Variables

### Required

| Name | Description | Default |
|------|-------------|---------|
| iam_name | SSH key identifier for resource access | &nbsp; |
| policy_name | Name of the IAM policy to be created | &nbsp; |

### Optional

| Name | Description | Default |
|------|-------------|---------|
| aws_default_region | Default AWS region | eu-west-1 |
| policy_hash | Base64 encoded IAM policy document | &nbsp; |
| allows_hash | Base64 encoded list of policy allow statements | &nbsp; |
| denies_hash | Base64 encoded list of policy deny statements | &nbsp; |

## Dependencies

### Substacks
- [config0-publish:::tf_executor](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/stacks/config0-publish/tf_executor/default)

### Execgroups
- [config0-publish:::aws::iam-keys](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/exec/groups/config0-publish/aws/iam-keys/default)

### Shelloutconfigs
- [config0-publish:::terraform::resource_wrapper](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/shelloutconfigs/config0-publish/terraform/resource_wrapper/default)

## License
<pre>
Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
</pre>
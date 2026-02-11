# AWS Lambda Function Stack

## Description
This stack creates and configures an AWS Lambda function with customizable settings for runtime, memory, timeout, and environment variables. It manages the deployment of Lambda code packages stored in S3 buckets.

## Variables

### Required Variables
| Name | Description | Default |
|------|-------------|---------|
| s3_bucket | S3 bucket name | &nbsp; |
| lambda_name | Lambda function name | &nbsp; |

### Optional Variables
| Name | Description | Default |
|------|-------------|---------|
| handler | Lambda function handler | app.handler |
| runtime | Configuration for runtime | python3.11 |
| memory_size | Configuration for memory size | 256 |
| lambda_timeout | Lambda function timeout (seconds) | 900 |
| lambda_layers | Lambda function layers | &nbsp; |
| s3_key | Lambda function code S3 key | &nbsp; |
| policy_template_hash | IAM policy templates in base64 | &nbsp; |
| lambda_env_vars_hash | Lambda environment variables in base64 | &nbsp; |
| aws_default_region | Default AWS region | eu-west-1 |

## Dependencies

### Substacks
- [config0-publish:::tf_executor](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/stacks/config0-publish/tf_executor/default)

### Execgroups
- [config0-publish:::aws::add_lambda](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/exec/groups/config0-publish/aws/add_lambda/default)

### Shelloutconfigs
- [config0-publish:::terraform::resource_wrapper](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/shelloutconfigs/config0-publish/terraform/resource_wrapper/default)

## License
<pre>
Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
</pre>

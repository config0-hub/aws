# AWS Lambda Function Stack

## Description
This stack creates and configures an AWS Lambda function with customizable settings for runtime, memory, timeout, and environment variables. It manages the deployment of Lambda code packages stored in S3 buckets.

## Variables

### Required Variables
| Name | Description | Default |
|------|-------------|---------|
| s3_bucket | S3 bucket name |  |
| lambda_name | Lambda function name |  |

### Optional Variables
| Name | Description | Default |
|------|-------------|---------|
| handler | Lambda function handler | app.handler |
| runtime | Configuration for runtime | python3.9 |
| memory_size | Configuration for memory size | 256 |
| lambda_timeout | Lambda function timeout (seconds) | 900 |
| lambda_layers | Lambda function layers |  |
| s3_key | Lambda function code S3 key |  |
| policy_template_hash | IAM policy templates in base64 |  |
| lambda_env_vars_hash | Lambda environment variables in base64 |  |
| aws_default_region | Default AWS region | eu-west-1 |

## Features
- Creates AWS Lambda functions with configurable settings
- Supports custom IAM policies
- Configurable environment variables
- Integration with S3 for Lambda code deployment
- Sets up proper logging permissions
- Default assume role policies for Lambda execution

## Dependencies

### Substacks
- [config0-publish:::tf_executor](https://api-app.config0.com/web_api/v1.0/stacks/config0-publish/tf_executor)

### Execgroups
- [config0-publish:::aws::add_lambda](https://api-app.config0.com/web_api/v1.0/exec/groups/config0-publish/aws/add_lambda)

## License
Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
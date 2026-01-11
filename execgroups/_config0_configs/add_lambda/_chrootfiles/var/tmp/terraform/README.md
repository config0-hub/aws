# AWS Lambda Terraform Module

This module provisions an AWS Lambda function with associated IAM role and policies.

## Overview

This Terraform module creates:
- AWS Lambda function with configurable runtime, memory, and timeout
- IAM role for Lambda execution
- IAM policy with necessary permissions
- IAM role policy attachment

## Requirements

- OpenTofu >= 1.5.0 (or Terraform)
- AWS Provider ~> 5.0
- Template Provider ~> 2.2

## Usage

```hcl
module "lambda_function" {
  source = "./path/to/module"
  
  lambda_name        = "my-function"
  s3_bucket          = "my-deployment-bucket"
  s3_key             = "path/to/lambda-code.zip"
  
  # Optional configurations
  runtime            = "python3.11"
  handler            = "app.handler"
  memory_size        = 256
  lambda_timeout     = 60
  lambda_layers      = "arn:aws:lambda:region:account:layer:name:version"
  
  lambda_env_vars = {
    ENV_NAME = "production"
    LOG_LEVEL = "INFO"
  }
  
  cloud_tags = {
    Environment = "production"
    Owner       = "platform-team"
  }
}
```

## Variables in Detail

### Required Variables

| Name | Description | Type |
|------|-------------|------|
| `lambda_name` | Name of the Lambda function | `string` |
| `s3_bucket` | S3 bucket containing the Lambda deployment package | `string` |
| `s3_key` | S3 key path to the Lambda deployment package | `string` |

### Optional Variables

| Name | Description | Type | Default |
|------|-------------|------|---------|
| `handler` | Lambda function handler entry point (e.g., "app.handler") | `string` | `"app.handler"` |
| `runtime` | Lambda runtime environment (e.g., "python3.11", "nodejs18.x") | `string` | `"python3.11"` |
| `memory_size` | Amount of memory in MB allocated to the Lambda function (128-10240) | `number` | `128` |
| `lambda_timeout` | Lambda function timeout in seconds (max 900) | `number` | `900` |
| `lambda_layers` | Comma-separated list of Lambda layer ARNs to attach to the function | `string` | `null` |
| `lambda_env_vars` | Environment variables for the Lambda function as key-value pairs | `map(string)` | `{}` |
| `aws_default_region` | AWS region where resources will be deployed | `string` | `"eu-west-1"` |
| `cloud_tags` | Additional tags to apply to all resources | `map(string)` | `{}` |
| `product` | Product name used for tagging | `string` | `"lambda"` |
| `assume_policy` | IAM policy document allowing Lambda service to assume the role | `string` | See below |
| `policy_template_hash` | Base64 encoded IAM policy template that will be rendered with variables | `string` | See below |

### Default IAM Assume Role Policy

The default assume role policy allows the Lambda service to assume this role:

```json
{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": "sts:AssumeRole",
     "Principal": {
       "Service": "lambda.amazonaws.com"
     },
     "Effect": "Allow",
     "Sid": ""
   }
 ]
}
```

### Default Lambda Policy

The default policy (in base64 encoded form) grants permissions for CloudWatch Logs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*",
      "Effect": "Allow"
    }
  ]
}
```

## Outputs

| Name | Description |
|------|-------------|
| `function_name` | The name of the Lambda function |
| `arn` | The ARN of the Lambda function |
| `invoke_arn` | The ARN to be used for invoking the Lambda function from API Gateway |
| `role` | The IAM role ARN attached to the Lambda function |
| `s3_bucket` | The S3 bucket containing the Lambda function's deployment package |
| `s3_key` | The S3 key of the Lambda function's deployment package |
| `memory_size` | The memory size allocated to the Lambda function |
| `runtime` | The runtime environment of the Lambda function |
| `handler` | The handler of the Lambda function |
| `layers` | The list of Lambda layer ARNs attached to the function |
| `timeout` | The function execution timeout in seconds |

## Notes

- The Lambda code should be packaged and uploaded to an S3 bucket before using this module
- IAM permissions are configured to allow Lambda to write logs to CloudWatch
- Additional permissions can be added by customizing the `policy_template_hash` variable
- The policy template can include template variables: `${aws_default_region}` and `${aws_account_id}`

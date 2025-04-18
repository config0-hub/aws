# AWS Lambda with CodeBuild

## Description

This stack creates an AWS Lambda function using AWS CodeBuild to package your Python code. It provides a seamless way to build and deploy Python code to AWS Lambda, handling all the necessary build processes through CodeBuild and deploying the resulting package to Lambda.

## Variables

### Required Variables

| Name | Description | Default |
|------|-------------|---------|
| config0_lambda_execgroup_name | Execution group name for the Lambda deployment | &nbsp; |
| lambda_name | Lambda function name | &nbsp; |
| s3_bucket | S3 bucket name | &nbsp; |

### Optional Variables

| Name | Description | Default |
|------|-------------|---------|
| handler | Lambda function handler | app.handler |
| runtime | Configuration for runtime | python3.8 |
| memory_size | Configuration for memory size | 256 |
| lambda_timeout | Lambda function timeout (seconds) | 900 |
| lambda_layers | Lambda function layers | &nbsp; |
| policy_template_hash | IAM policy templates in base64 | &nbsp; |
| aws_default_region | Default AWS region | us-east-1 |
| lambda_env_vars_hash | Lambda environment variables in base64 | &nbsp; |
| cloud_tags_hash | Resource tags for cloud provider | null |
| stateful_id | Stateful ID for storing the resource code/state | _random |
| share_dir | Directory for sharing files between containers | /var/tmp/share |
| script_name | Script name to run in codebuild | docker-to-lambda.sh |
| codebuild_role | IAM role for CodeBuild service | config0-assume-poweruser |
| compute_type | Configuration for compute type | BUILD_GENERAL1_SMALL |
| image_type | Configuration for image type | LINUX_CONTAINER |
| build_timeout | Configuration for build timeout | 900 |

## Dependencies

### Substacks
- [config0-publish:::aws_lambda](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/stacks/config0-publish/aws_lambda/default)

### Execgroups
- [config0-publish:::aws::py_to_lambda-codebuild](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/exec/groups/config0-publish/aws/py_to_lambda-codebuild/default)

### Shelloutconfigs
- [config0-publish:::terraform::resource_wrapper](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/shelloutconfigs/config0-publish/terraform/resource_wrapper/default)

## License
<pre>
Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
</pre>
# AWS CodeBuild Notifications Module

This OpenTofu/Terraform module sets up a notification system that sends AWS CodeBuild state change events to a Lambda function via SNS. The module configures:

1. An SNS topic for build notifications
2. Subscription of a Lambda function to the SNS topic
3. CloudWatch Event Rule to capture CodeBuild state changes
4. Necessary IAM permissions

## Usage

```hcl
module "codebuild_notifications" {
  source             = "./path/to/module"
  topic_name         = "codebuild-notifications"
  aws_default_region = "us-west-2"
  lambda_name        = "my-notification-handler"
  cloud_tags         = {
    Environment = "production"
    Project     = "my-project"
  }
}
```

## Requirements

- OpenTofu >= 1.8.8 or Terraform >= 1.0.0
- AWS Provider >= 4.0.0

## Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `topic_name` | The name of the SNS topic to which the build notifications will be sent | `string` | n/a | yes |
| `aws_default_region` | The AWS region where resources will be created (e.g., eu-west-1) | `string` | n/a | yes |
| `lambda_name` | The name of the Lambda function that will process the SNS notifications | `string` | n/a | yes |
| `cloud_tags` | Additional tags to apply to created resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| `sns_topic_arn` | ARN of the created SNS topic |
| `cloudwatch_name` | Name of the CloudWatch event rule |
| `cloudwatch_arn` | ARN of the CloudWatch event rule |
| `sns_topic_subscription` | The SNS topic subscription details showing source and destination |
| `endpoint` | The Lambda endpoint that receives the SNS notifications |

## Notes

- By default, this module captures all CodeBuild projects' state changes (STOPPED, FAILED, SUCCEEDED)
- To filter for specific CodeBuild projects, you would need to modify the CloudWatch event pattern

## License

Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
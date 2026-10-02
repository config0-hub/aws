# AWS ECS Service Module

This OpenTofu module creates an AWS ECS cluster and one Fargate service with ECS Exec on.

## Features

- Creates an ECS cluster and a Fargate task definition running `public.ecr.aws/docker/library/nginx:stable`
- Creates one ECS service, one task by default, in the given subnets and security groups, with no public IP
- Turns ECS Exec on; the task role carries the `ssmmessages` channel permissions it needs
- Creates the task execution role (`AmazonECSTaskExecutionRolePolicy`) and a CloudWatch log group

## Usage

```hcl
module "ecs_service" {
  source = "./path/to/module"

  ecs_cluster = "my-cluster"
  ecs_service = "web"

  subnet_ids         = ["subnet-1234abcd", "subnet-5678efgh"]
  security_group_ids = ["sg-1234abcd"]

  cloud_tags = {
    Environment = "production"
  }
}
```

## Requirements

- OpenTofu >= 1.8.8
- AWS Provider
- The subnets reach the internet (NAT gateway) or VPC endpoints, for the image pull and `ssmmessages`

## Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| aws_default_region | The AWS region where resources will be created | `string` | `"us-east-1"` | no |
| ecs_cluster | The name of the ECS cluster | `string` | n/a | yes |
| ecs_service | The name of the ECS service, its task definition family and its container | `string` | n/a | yes |
| subnet_ids | List of subnet IDs the service's tasks run in | `list(string)` | n/a | yes |
| security_group_ids | List of VPC security group IDs to associate with the service's tasks | `list(string)` | n/a | yes |
| image | The container image the task runs | `string` | `"public.ecr.aws/docker/library/nginx:stable"` | no |
| container_port | The port the container listens on | `number` | `80` | no |
| cpu | The Fargate task CPU units | `number` | `256` | no |
| memory | The Fargate task memory in MiB | `number` | `512` | no |
| desired_count | The number of tasks the service keeps running | `number` | `1` | no |
| log_retention_in_days | The CloudWatch log group retention in days | `number` | `7` | no |
| cloud_tags | Additional tags as a map to apply to all resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| ecs_cluster | The name of the ECS cluster |
| ecs_service | The name of the ECS service |
| arn | The ARN of the ECS service |
| cluster_arn | The ARN of the ECS cluster |
| task_definition_arn | The ARN of the task definition, with its revision |
| task_role_arn | The ARN of the task role |
| execution_role_arn | The ARN of the task execution role |
| log_group_name | The name of the CloudWatch log group |
| launch_type | The launch type of the ECS service |
| desired_count | The number of tasks the service keeps running |
| enable_execute_command | Whether ECS Exec is on for the service |

## License

Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

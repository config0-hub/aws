# AWS ECS Service Stack

## Description
This stack creates an AWS ECS cluster and one Fargate service running `public.ecr.aws/docker/library/nginx:stable`, one task by default, in private subnets with no public IP. ECS Exec is on: the task role carries the `ssmmessages` channel permissions, and the execution role carries `AmazonECSTaskExecutionRolePolicy`. The container logs go to a CloudWatch log group. The resource row carries `ecs_cluster` and `ecs_service`, the target fields an `ecs_access` grant takes.

The subnets need a route to the internet (a NAT gateway) or VPC endpoints, so the task can pull the image and reach `ssmmessages`. The role names are `<ecs_cluster>-task` and `<ecs_cluster>-execution`, so `ecs_cluster` is at most 54 characters. The service has no load balancer, so it has no endpoint.

## Variables

### Required Variables

| Name | Description | Default |
|------|-------------|---------|
| subnet_ids | Subnet ID list | &nbsp; |
| sg_id | Security group ID | &nbsp; |
| ecs_cluster | ECS cluster name | &nbsp; |

### Optional Variables

| Name | Description | Default |
|------|-------------|---------|
| ecs_service | ECS service name | the `ecs_cluster` value |
| cpu | Fargate task CPU units | `256` |
| memory | Fargate task memory in MiB | `512` |
| desired_count | Number of tasks the service keeps running | `1` |
| aws_default_region | Default AWS region | `eu-west-1` |

## Dependencies

### Substacks
- [config0-hub:::config0_core::tf_executor](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/stacks/config0-hub/tf_executor/default)

### Execgroups
- [config0-hub:::aws::ecs_service](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/exec/groups/config0-hub/aws/ecs_service/default)

### Scripts
- [config0-hub:::terraform::resource_wrapper](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/scripts/config0-hub/terraform/resource_wrapper/default)

## License
<pre>
Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
</pre>

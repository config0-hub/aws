# One ECS grant's inline permissions policy, per level (exec).
#
# Provider-free on purpose: tests/authoring-guards/test_access_inline_policy.py
# evaluates it with `tofu console` and no AWS access. Levels follow the CON-11
# contract (ops work-log 2026-09-24/con-11-access-requests/contract.md,
# section 2b).
#
# Sources:
#   "Using IAM policies to limit access to ECS Exec",
#   https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html
#   Service Authorization Reference, Amazon ECS:
#   https://docs.aws.amazon.com/service-authorization/latest/reference/list_ecs.html
#   (ExecuteCommand: cluster* and task*, condition keys ecs:cluster and
#   ecs:container-name; DescribeTasks: task*; DescribeServices: service*;
#   ListTasks: container-instance*, condition key ecs:cluster)
#   Amazon ECS identity-based policy examples (ListTasks on * with ecs:cluster),
#   https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security_iam_id-based-policy-examples.html
#
# Scope: exec reaches every task in the cluster, not only the service's. IAM
# scopes ecs:ExecuteCommand by cluster, task ARN or task tag; a task names its
# service only in the ECS managed tag aws:ecs:serviceName, present only when the
# service turns ECS managed tags on.

variable "level" {
  description = "The grant's ECS access level: exec"
  type        = string
}

variable "ecs_cluster" {
  description = "The target ECS cluster name"
  type        = string
}

variable "ecs_service" {
  description = "The target ECS service name"
  type        = string
}

variable "aws_account_id" {
  description = "Account the cluster lives in"
  type        = string
}

variable "aws_default_region" {
  description = "Region the cluster lives in"
  type        = string
}

locals {
  cluster_arn = "arn:aws:ecs:${var.aws_default_region}:${var.aws_account_id}:cluster/${var.ecs_cluster}"
  tasks_arn   = "arn:aws:ecs:${var.aws_default_region}:${var.aws_account_id}:task/${var.ecs_cluster}/*"
  service_arn = "arn:aws:ecs:${var.aws_default_region}:${var.aws_account_id}:service/${var.ecs_cluster}/${var.ecs_service}"

  in_cluster = {
    ArnEquals = { "ecs:cluster" = local.cluster_arn }
  }

  statements = {
    exec = [
      {
        # Any container: no ecs:container-name condition.
        Sid       = "ExecuteCommand"
        Effect    = "Allow"
        Action    = ["ecs:ExecuteCommand", "ecs:DescribeTasks"]
        Resource  = [local.cluster_arn, local.tasks_arn]
        Condition = local.in_cluster
      },
      {
        Sid      = "DescribeService"
        Effect   = "Allow"
        Action   = ["ecs:DescribeServices"]
        Resource = [local.service_arn]
      },
      {
        # ListTasks takes only the container-instance resource, which a
        # Fargate task has none of; AWS's example scopes it by ecs:cluster on *.
        Sid       = "ListTasks"
        Effect    = "Allow"
        Action    = ["ecs:ListTasks"]
        Resource  = "*"
        Condition = local.in_cluster
      },
      {
        # The exec session's data channel. ssmmessages "does not support
        # specifying a resource ARN",
        # https://docs.aws.amazon.com/service-authorization/latest/reference/list_ssmmessages.html
        # End-user OpenDataChannel: "Sample IAM policies for Session Manager",
        # https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-restrict-access-quickstart.html
        Sid      = "NoResourceArn"
        Effect   = "Allow"
        Action   = ["ssmmessages:OpenDataChannel"]
        Resource = "*"
      },
    ]
  }

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = local.statements[var.level]
  })
}

output "policy" {
  description = "The inline permissions policy JSON for the grant's level"
  value       = local.policy
}

# One ElastiCache grant's inline permissions policy and cache user access
# string, per level (read, read_write).
#
# Provider-free on purpose: tests/authoring-guards/test_access_inline_policy.py
# evaluates it with `tofu console` and no AWS access. Levels follow the CON-11
# contract (ops work-log 2026-09-24/con-11-access-requests/contract.md,
# section 2b).
#
# Sources:
#   "Authenticating with IAM" (ElastiCache): the role needs elasticache:Connect
#   on the cache and on the ElastiCache user; the sample policy names
#   arn:aws:elasticache:<region>:<account>:serverlesscache:<name> and
#   arn:aws:elasticache:<region>:<account>:user:<user id>; an IAM-enabled
#   user's user name and user id must be identical; cache names are stored
#   lowercase,
#   https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/auth-iam.html
#   Service Authorization Reference, Amazon ElastiCache:
#   https://docs.aws.amazon.com/service-authorization/latest/reference/list_elasticache.html
#   (Connect: replicationgroup, serverlesscache and user*; replication group
#   ARN arn:aws:elasticache:<region>:<account>:replicationgroup:<id>)
#   CreateUser API reference: UserId has a minimum length of 1 and the pattern
#   [a-zA-Z][a-zA-Z0-9\-]*, and no maximum,
#   https://docs.aws.amazon.com/AmazonElastiCache/latest/APIReference/API_CreateUser.html
#   Access strings: "Role-Based Access Control (RBAC)", "Specifying
#   Permissions Using an Access String",
#   https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Clusters.RBAC.html
#
# Every statement names the cache and the user, so the policy carries no "*".

variable "level" {
  description = "The grant's ElastiCache access level: read or read_write"
  type        = string
}

variable "role_name" {
  description = "The grant's role name; the ElastiCache user id and user name"
  type        = string
}

variable "cache_name" {
  description = "The replication group id or serverless cache name"
  type        = string
}

variable "cache_type" {
  description = "replication_group or serverless"
  type        = string
}

variable "aws_account_id" {
  description = "Account the cache lives in"
  type        = string
}

variable "aws_default_region" {
  description = "Region the cache lives in"
  type        = string
}

locals {
  # ElastiCache documents no maximum user id length; the role name fits the
  # user id pattern as it is.
  cache_user_id = var.role_name

  arn_prefix = "arn:aws:elasticache:${var.aws_default_region}:${var.aws_account_id}"
  cache_arns = {
    replication_group = "${local.arn_prefix}:replicationgroup:${lower(var.cache_name)}"
    serverless        = "${local.arn_prefix}:serverlesscache:${lower(var.cache_name)}"
  }
  user_arn = "${local.arn_prefix}:user:${local.cache_user_id}"

  access_strings = {
    read       = "on ~* +@read"
    read_write = "on ~* +@all"
  }

  # Both levels connect the same way; the access string sets what the user
  # may run once connected.
  connect = [
    {
      Sid      = "Connect"
      Effect   = "Allow"
      Action   = ["elasticache:Connect"]
      Resource = [local.cache_arns[var.cache_type], local.user_arn]
    },
  ]

  statements = {
    read       = local.connect
    read_write = local.connect
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

output "cache_user_id" {
  description = "The grant's ElastiCache user id, also its user name"
  value       = local.cache_user_id
}

output "access_string" {
  description = "The ElastiCache user's access string for the grant's level"
  value       = local.access_strings[var.level]
}

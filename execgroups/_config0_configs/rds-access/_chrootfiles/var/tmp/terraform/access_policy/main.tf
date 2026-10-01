# One RDS grant's inline permissions policy, per level (connect, read_only,
# read_write).
#
# Provider-free on purpose: tests/authoring-guards/test_access_inline_policy.py
# evaluates it with `tofu console` and no AWS access. Levels follow the CON-11
# contract (ops work-log 2026-09-24/con-11-access-requests/contract.md,
# section 2b).
#
# Sources:
#   "Creating and using an IAM policy for IAM database access" (RDS),
#   https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.IAMPolicy.html
#   (rds-db:connect on "one database account in one DB instance":
#   arn:aws:rds-db:<region>:<account-id>:dbuser:<DbiResourceId>/<db-user-name>)
#   The same page for Aurora,
#   https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.IAMDBAuth.IAMPolicy.html
#   (the DbClusterResourceId, cluster-..., takes the DbiResourceId's place)
#   "Creating a database account using IAM authentication",
#   https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.DBAccounts.html
#   ("Make sure the specified database user name is the same as a resource in
#   the IAM policy"; the user name must match its case in the database)
#
# The level changes only what the database user may do inside the database,
# granted by the rds-access-user script; IAM gates the log on alone, so every
# level carries the same one statement. It names one database user on one
# instance or cluster, so the policy carries no "*" resource.

variable "level" {
  description = "The grant's RDS access level: connect, read_only or read_write"
  type        = string
}

variable "grant_id" {
  description = "The grant id, 32 lowercase hex; the database user is derived from it"
  type        = string
}

variable "db_resource_id" {
  description = "The DbiResourceId (db-...) or the Aurora DbClusterResourceId (cluster-...)"
  type        = string
}

variable "aws_account_id" {
  description = "Account the database lives in"
  type        = string
}

variable "aws_default_region" {
  description = "Region the database lives in"
  type        = string
}

locals {
  # c0_ and the first 16 hex of the grant id: 19 characters, inside MySQL's
  # 32-character user name limit. The rds_access stack derives the same name.
  db_user = "c0_${substr(var.grant_id, 0, 16)}"

  connect = [
    {
      Sid      = "Connect"
      Effect   = "Allow"
      Action   = ["rds-db:connect"]
      Resource = ["arn:aws:rds-db:${var.aws_default_region}:${var.aws_account_id}:dbuser:${var.db_resource_id}/${local.db_user}"]
    },
  ]

  statements = {
    connect    = local.connect
    read_only  = local.connect
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

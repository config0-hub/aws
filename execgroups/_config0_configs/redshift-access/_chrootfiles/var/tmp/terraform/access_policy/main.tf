# One Redshift grant's inline permissions policy, per level (connect).
#
# Provider-free on purpose: tests/authoring-guards/test_access_inline_policy.py
# evaluates it with `tofu console` and no AWS access. Levels follow the CON-11
# contract (ops work-log 2026-09-24/con-11-access-requests/contract.md,
# section 2b).
#
# Sources:
#   "Using identity-based policies (IAM policies) for Amazon Redshift",
#   https://docs.aws.amazon.com/redshift/latest/mgmt/redshift-iam-access-control-identity-based.html
#   ("Resource policies for GetClusterCredentials" and "Example 8: IAM policy
#   for using GetClusterCredentials". The ARN formats
#   arn:aws:redshift:<region>:<account>:dbuser:<cluster>/<dbuser>,
#   ...:dbname:<cluster>/<dbname> and ...:dbgroup:<cluster>/<dbgroup>.
#   Autocreate needs redshift:CreateClusterUser on the dbuser; DbGroups needs
#   redshift:JoinGroup on each dbgroup; connecting by cluster id needs
#   redshift:DescribeClusters on the cluster.)
#   GetClusterCredentials API reference: DbUser is 1 to 64 characters, the
#   first a letter; "If DbName is not specified, DbUser can log on to any
#   existing database",
#   https://docs.aws.amazon.com/redshift/latest/APIReference/API_GetClusterCredentials.html
#   Service Authorization Reference, Amazon Redshift:
#   https://docs.aws.amazon.com/service-authorization/latest/reference/list_redshift.html
#   (GetClusterCredentials: dbname and dbuser*, condition key redshift:DbName;
#   CreateClusterUser: dbuser*; JoinGroup: dbgroup*; DescribeClusters: cluster,
#   arn:aws:redshift:<region>:<account>:cluster:<cluster>)
#
# The database user: GetClusterCredentials with Autocreate=true creates it on
# the first call, so no user is pre-created. Once created it is the user's own
# and Config0 never deletes it; removing the grant removes the role only.
# Every statement names a cluster ARN, so the policy carries no "*" resource.

variable "level" {
  description = "The grant's Redshift access level: connect"
  type        = string
}

variable "role_name" {
  description = "The grant's role name; the database user is derived from it"
  type        = string
}

variable "redshift_cluster" {
  description = "The target Redshift cluster identifier"
  type        = string
}

variable "db_name" {
  description = "The one database the credentials log on to"
  type        = string
}

variable "db_groups" {
  description = "Existing database groups the user joins at log on; may be empty"
  type        = list(string)
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
  # DbUser: at most 64 characters. The role name starts with a letter.
  db_user = substr(lower(var.role_name), 0, 64)

  arn_prefix   = "arn:aws:redshift:${var.aws_default_region}:${var.aws_account_id}"
  cluster_arn  = "${local.arn_prefix}:cluster:${var.redshift_cluster}"
  dbuser_arn   = "${local.arn_prefix}:dbuser:${var.redshift_cluster}/${local.db_user}"
  dbname_arn   = "${local.arn_prefix}:dbname:${var.redshift_cluster}/${var.db_name}"
  dbgroup_arns = [for group in var.db_groups : "${local.arn_prefix}:dbgroup:${var.redshift_cluster}/${group}"]

  connect = [
    {
      # Without DbName the credentials log on to any database; the condition
      # requires DbName and pins it to the grant's database.
      Sid       = "GetClusterCredentials"
      Effect    = "Allow"
      Action    = ["redshift:GetClusterCredentials"]
      Resource  = [local.dbuser_arn, local.dbname_arn]
      Condition = { StringEquals = { "redshift:DbName" = var.db_name } }
    },
    {
      # Autocreate=true: Redshift creates the user on the first call.
      Sid      = "CreateClusterUser"
      Effect   = "Allow"
      Action   = ["redshift:CreateClusterUser"]
      Resource = [local.dbuser_arn]
    },
    {
      Sid      = "DescribeCluster"
      Effect   = "Allow"
      Action   = ["redshift:DescribeClusters"]
      Resource = [local.cluster_arn]
    },
  ]

  # IAM refuses a statement with an empty Resource, so no groups, no statement.
  join_groups = length(local.dbgroup_arns) == 0 ? [] : [
    {
      Sid      = "JoinGroups"
      Effect   = "Allow"
      Action   = ["redshift:JoinGroup"]
      Resource = local.dbgroup_arns
    },
  ]

  statements = {
    connect = concat(local.connect, local.join_groups)
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

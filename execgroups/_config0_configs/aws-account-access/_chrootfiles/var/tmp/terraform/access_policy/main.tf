# The inline deny every aws_account grant's role carries, at every level.
#
# Provider-free on purpose: tests/authoring-guards/test_access_inline_policy.py
# evaluates it with `tofu console` and no AWS access. Names follow the CON-11
# contract (ops work-log 2026-09-24/con-11-access-requests/contract.md,
# section 2b).
#
# Why (CON-11 review round 1, finding F1): Config0 keeps secrets in this
# account's Parameter Store under /config0/: a db_password grant's password
# copy and every input-variable set. They are SecureStrings under the
# AWS-managed aws/ssm key, whose key policy lets any principal in the account
# that may call SSM decrypt through it. ReadOnlyAccess carries ssm:Get*, so an
# auto-approved read_only grant, which no org admin sees, could read the
# password a db_password grant keeps behind an org admin. The managed policy
# of any level stays attached; this deny carves the Config0 secrets out.
#
# ssm:GetParameter* names the /config0 path. The path itself is listed too: a
# caller allowed on a parent path reads /config0/... through a recursive
# GetParametersByPath even when the parameter is denied ("Restricting access
# to Parameter Store parameters using IAM policies",
# https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-access.html).
# A recursive read from / is closed by the kms:Decrypt deny, which matches
# Parameter Store's encryption context PARAMETER_ARN, so it holds for any key
# the parameter uses; its resource is `*` because the aws/ssm key's ARN
# differs per account and region ("How AWS Systems Manager Parameter Store
# uses AWS KMS",
# https://docs.aws.amazon.com/kms/latest/developerguide/services-parameter-store.html).
#
# ssm:DescribeParameters is not denied: it takes only a `*` resource, so a
# deny on the /config0 path never matches it, and it returns names and
# metadata, never values.
#
# Limit: at the admin level the grantee may delete this policy from its own
# role; the deny binds every other level.

variable "aws_account_id" {
  description = "The target account; its Config0 parameters are denied"
  type        = string
}

locals {
  config0_parameters = [
    "arn:aws:ssm:*:${var.aws_account_id}:parameter/config0",
    "arn:aws:ssm:*:${var.aws_account_id}:parameter/config0/*",
  ]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "DenyConfig0Parameters"
        Effect   = "Deny"
        Action   = ["ssm:GetParameter*"]
        Resource = local.config0_parameters
      },
      {
        Sid      = "DenyConfig0ParameterDecrypt"
        Effect   = "Deny"
        Action   = ["kms:Decrypt"]
        Resource = "*"
        Condition = {
          StringLike = { "kms:EncryptionContext:PARAMETER_ARN" = local.config0_parameters }
        }
      },
    ]
  })
}

output "policy" {
  description = "The inline deny policy JSON, the same at every level"
  value       = local.policy
}

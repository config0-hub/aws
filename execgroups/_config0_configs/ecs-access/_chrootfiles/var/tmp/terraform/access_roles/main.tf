# One grant's role name and trust policy.
#
# Provider-free on purpose: tests/authoring-guards/test_eks_access_trust_policy.py
# evaluates it with `tofu console` and no AWS access. Names and shapes follow
# the CON-11 contract (ops work-log 2026-09-24/con-11-access-requests/contract.md).

variable "grant_id" {
  description = "The grant id, 32 lowercase hex; names the role"
  type        = string
}

variable "aws_account_id" {
  description = "Account the target and the role live in"
  type        = string
}

variable "source_identity" {
  description = "The grantee's owner id; the only sts:SourceIdentity the role trusts"
  type        = string

  validation {
    condition     = can(regex("^[\\w+=,.@-]{2,64}$", var.source_identity))
    error_message = "source_identity must match the IAM SourceIdentity rule [\\w+=,.@-]{2,64}."
  }
}

variable "end_time" {
  description = "UTC ISO 8601 end of the grant; the role trusts no session after it"
  type        = string

  validation {
    condition     = can(formatdate("YYYY", var.end_time))
    error_message = "end_time must be a UTC ISO 8601 (RFC 3339) timestamp."
  }
}

locals {
  role_name = "config0-access-${var.grant_id}"

  trust_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::${var.aws_account_id}:role/config0-executor-remote" }
      Action    = ["sts:AssumeRole", "sts:SetSourceIdentity"]
      Condition = {
        StringEquals = { "sts:SourceIdentity" = var.source_identity }
        DateLessThan = { "aws:CurrentTime" = var.end_time }
      }
    }]
  })
}

output "role_name" {
  description = "The grant's role name"
  value       = local.role_name
}

output "trust_policy" {
  description = "Trust policy JSON: one statement for the grantee until the end time"
  value       = local.trust_policy
}

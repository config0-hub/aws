# AWS account access grant: one IAM role for one grantee until the end time,
# with the AWS managed policy of the grant's level attached and the inline
# deny of ./access_policy on Config0's Parameter Store secrets. The role name
# and trust policy come from ./access_roles. Names follow the CON-11 contract (ops
# work-log 2026-09-24/con-11-access-requests/contract.md, section 2b).
#
# The managed policies are the one place an access grant attaches a broad
# policy, by design: the target is the whole account. ARNs from the AWS Managed
# Policy Reference:
#   https://docs.aws.amazon.com/aws-managed-policy/latest/reference/ReadOnlyAccess.html
#   https://docs.aws.amazon.com/aws-managed-policy/latest/reference/ViewOnlyAccess.html
#   https://docs.aws.amazon.com/aws-managed-policy/latest/reference/PowerUserAccess.html
#   https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AdministratorAccess.html
#   https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SecurityAudit.html
#   https://docs.aws.amazon.com/aws-managed-policy/latest/reference/Billing.html

locals {
  # The aws_account level set, fixed per stack version; the aws_account_access
  # stack's run.py carries the same level names.
  levels = {
    read_only      = "arn:aws:iam::aws:policy/ReadOnlyAccess"
    view_only      = "arn:aws:iam::aws:policy/job-function/ViewOnlyAccess"
    power_user     = "arn:aws:iam::aws:policy/PowerUserAccess"
    admin          = "arn:aws:iam::aws:policy/AdministratorAccess"
    security_audit = "arn:aws:iam::aws:policy/SecurityAudit"
    billing        = "arn:aws:iam::aws:policy/job-function/Billing"
  }
}

module "access_roles" {
  source = "./access_roles"

  grant_id        = var.grant_id
  aws_account_id  = var.aws_account_id
  source_identity = var.grantee_owner_id
  end_time        = var.end_time
}

# The same deny at every level: no count, no for_each.
module "access_policy" {
  source = "./access_policy"

  aws_account_id = var.aws_account_id
}

resource "aws_iam_role" "access" {
  name               = module.access_roles.role_name
  assume_role_policy = module.access_roles.trust_policy

  tags = var.cloud_tags
}

resource "aws_iam_role_policy_attachment" "level" {
  role       = aws_iam_role.access.name
  policy_arn = local.levels[var.level]
}

resource "aws_iam_role_policy" "config0_secrets_deny" {
  name   = module.access_roles.role_name
  role   = aws_iam_role.access.id
  policy = module.access_policy.policy
}

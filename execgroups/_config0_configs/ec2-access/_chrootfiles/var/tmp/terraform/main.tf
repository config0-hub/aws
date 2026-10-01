# EC2 access grant: one IAM role for one grantee until the end time, with one
# inline policy for the grant's level on one instance. Covers the ec2 kind
# (session, port_forward, ssh) and the ec2_windows kind (rdp). The role name
# and trust policy come from ./access_roles; the permissions policy from
# ./access_policy, which cites the AWS page for every statement. Names follow
# the CON-11 contract (ops work-log 2026-09-24/con-11-access-requests/
# contract.md, section 2b).

module "access_roles" {
  source = "./access_roles"

  grant_id        = var.grant_id
  aws_account_id  = var.aws_account_id
  source_identity = var.grantee_owner_id
  end_time        = var.end_time
}

module "access_policy" {
  source = "./access_policy"

  level              = var.level
  instance_id        = var.instance_id
  aws_account_id     = var.aws_account_id
  aws_default_region = var.aws_default_region
}

resource "aws_iam_role" "access" {
  name               = module.access_roles.role_name
  assume_role_policy = module.access_roles.trust_policy

  tags = var.cloud_tags
}

resource "aws_iam_role_policy" "level" {
  name   = module.access_roles.role_name
  role   = aws_iam_role.access.id
  policy = module.access_policy.policy
}

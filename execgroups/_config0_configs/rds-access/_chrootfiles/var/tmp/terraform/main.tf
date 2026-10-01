# RDS access grant: one IAM role for one grantee until the end time, with one
# inline policy for IAM database authentication as the grant's database user
# on one DB instance or Aurora cluster. The role name and trust policy come
# from ./access_roles; the permissions policy from ./access_policy, which
# cites the AWS pages. The database user itself is created before this apply
# by the rds-access-user script group on a host in the VPC; nothing here
# reaches into the database. Names follow the CON-11 contract (ops work-log
# 2026-09-24/con-11-access-requests/contract.md, section 2b).

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
  grant_id           = var.grant_id
  db_resource_id     = var.db_resource_id
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

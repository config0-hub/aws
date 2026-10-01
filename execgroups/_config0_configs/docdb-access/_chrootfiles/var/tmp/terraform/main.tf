# DocumentDB access grant: one IAM role for one grantee until the end time,
# with no permissions policy. The role name and trust policy come from
# ./access_roles. DocumentDB checks no IAM action on connect: the role's ARN,
# the user name of the $external user the docdb-access-user script group
# creates before this apply, is what lets the role in ("Authentication using
# IAM identity", Amazon DocumentDB,
# https://docs.aws.amazon.com/documentdb/latest/developerguide/iam-identity-auth.html).
# Names follow the CON-11 contract (ops work-log 2026-09-24/
# con-11-access-requests/contract.md, section 2b).

module "access_roles" {
  source = "./access_roles"

  grant_id        = var.grant_id
  aws_account_id  = var.aws_account_id
  source_identity = var.grantee_owner_id
  end_time        = var.end_time
}

resource "aws_iam_role" "access" {
  name               = module.access_roles.role_name
  assume_role_policy = module.access_roles.trust_policy

  tags = var.cloud_tags
}

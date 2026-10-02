# ElastiCache access grant: one IAM role for one grantee until the end time,
# with one inline policy for elasticache:Connect, and one IAM-authenticated
# ElastiCache user in the cache's existing user group. The role name and trust
# policy come from ./access_roles; the permissions policy, the user id and the
# access string from ./access_policy, which cites the AWS page for each. Names
# follow the CON-11 contract (ops work-log 2026-09-24/con-11-access-requests/
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
  grant_id           = var.grant_id
  cache_name         = var.cache_name
  cache_type         = var.cache_type
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

# An IAM-enabled user: user id and user name identical ("Authenticating with
# IAM", https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/auth-iam.html).
resource "aws_elasticache_user" "access" {
  user_id       = module.access_policy.cache_user_id
  user_name     = module.access_policy.cache_user_id
  engine        = var.engine
  access_string = module.access_policy.access_string

  authentication_mode {
    type = "iam"
  }

  tags = var.cloud_tags
}

# Adds the user to the cache's existing user group without owning the group
# (provider docs, aws_elasticache_user_group_association,
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticache_user_group_association).
# The destroy removes only this membership and this user.
resource "aws_elasticache_user_group_association" "access" {
  user_group_id = var.user_group_id
  user_id       = aws_elasticache_user.access.user_id
}

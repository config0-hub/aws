# EKS access grant: one IAM role for one grantee until the end time, one EKS
# access entry, one access policy association at the grant's level, and one
# inline policy allowing eks:DescribeCluster on the cluster. The role name and
# trust policy come from ./access_roles; the permissions policy from
# ./access_policy, which cites the AWS pages. Names follow the CON-11 contract
# (ops work-log 2026-09-24/con-11-access-requests/contract.md).

locals {
  # The EKS level set, fixed per stack version; the eks_access stack's run.py
  # carries the same table.
  levels = {
    view = {
      policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy"
      scope      = "cluster"
    }
    edit = {
      policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"
      scope      = "namespace"
    }
    admin = {
      policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy"
      scope      = "namespace"
    }
    cluster_admin = {
      policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
      scope      = "cluster"
    }
  }

  level = local.levels[var.level]
}

module "access_roles" {
  source = "./access_roles"

  grant_id        = var.grant_id
  aws_account_id  = var.aws_account_id
  source_identity = var.grantee_owner_id
  end_time        = var.end_time
}

module "access_policy" {
  source = "./access_policy"

  eks_cluster        = var.eks_cluster
  aws_account_id     = var.aws_account_id
  aws_default_region = var.aws_default_region
}

resource "aws_iam_role" "access" {
  name               = module.access_roles.role_name
  assume_role_policy = module.access_roles.trust_policy

  tags = var.cloud_tags
}

# `aws eks update-kubeconfig` needs eks:DescribeCluster; the access policy
# association below grants Kubernetes permissions only.
resource "aws_iam_role_policy" "describe_cluster" {
  name   = module.access_roles.role_name
  role   = aws_iam_role.access.id
  policy = module.access_policy.policy
}

# Precedent: aws_eks_access_entry.role_access in aws_eks eks-cluster-auto.
resource "aws_eks_access_entry" "role_access" {
  cluster_name  = var.eks_cluster
  principal_arn = aws_iam_role.access.arn
  type          = "STANDARD"

  tags = var.cloud_tags
}

resource "aws_eks_access_policy_association" "role_policy" {
  cluster_name  = var.eks_cluster
  policy_arn    = local.level.policy_arn
  principal_arn = aws_eks_access_entry.role_access.principal_arn

  access_scope {
    type       = local.level.scope
    namespaces = local.level.scope == "namespace" ? var.namespaces : null
  }
}

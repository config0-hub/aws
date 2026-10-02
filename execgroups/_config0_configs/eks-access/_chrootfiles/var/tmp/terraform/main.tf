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

# An access entry needs the cluster's authentication mode API or
# API_AND_CONFIG_MAP. Config0 does not change a user's cluster: the role is
# the first resource every other one reads, so a refused grant creates
# nothing (CON-11 contract, section 2b).
#
# The cluster is read only when it is in the cluster list: a person may delete
# their cluster before removing the grant, and the removal must still destroy
# the role (contract, section 9). Preconditions are not evaluated on destroy,
# so a removal with the cluster gone plans with count 0 and converges.
data "aws_eks_clusters" "all" {}

data "aws_eks_cluster" "target" {
  count = contains(data.aws_eks_clusters.all.names, var.eks_cluster) ? 1 : 0

  name = var.eks_cluster
}

locals {
  # null when the cluster is not in this account and region.
  cluster_mode = one(data.aws_eks_cluster.target[*].access_config[0].authentication_mode)
}

resource "aws_iam_role" "access" {
  name               = module.access_roles.role_name
  assume_role_policy = module.access_roles.trust_policy

  tags = var.cloud_tags

  lifecycle {
    precondition {
      condition     = length(data.aws_eks_cluster.target) == 1
      error_message = "EKS cluster ${var.eks_cluster} was not found in account ${var.aws_account_id} region ${var.aws_default_region}."
    }
    precondition {
      condition     = local.cluster_mode == null ? true : contains(["API", "API_AND_CONFIG_MAP"], local.cluster_mode)
      error_message = "EKS cluster ${var.eks_cluster} has authentication mode ${local.cluster_mode}. The cluster's authentication mode must be API or API_AND_CONFIG_MAP before an access grant; Config0 does not change it."
    }
  }
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

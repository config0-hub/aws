# One EKS grant's inline permissions policy: eks:DescribeCluster on the one
# cluster. EKS access policies carry Kubernetes permissions only; the grant's
# ready command `aws eks update-kubeconfig` needs eks:DescribeCluster on the
# cluster, so every level carries this one statement.
#
# Provider-free on purpose: tests/authoring-guards/test_access_inline_policy.py
# evaluates it with `tofu console` and no AWS access. Follows the CON-11
# contract (ops work-log 2026-09-24/con-11-access-requests/contract.md,
# section 2).
#
# Sources:
#   "Connect kubectl to an EKS cluster by creating a kubeconfig file",
#   https://docs.aws.amazon.com/eks/latest/userguide/create-kubeconfig.html
#   ("the eks:DescribeCluster API action for the cluster that you specify")
#   Service Authorization Reference, Amazon EKS:
#   https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html
#   (DescribeCluster: cluster*, arn:aws:eks:<region>:<account>:cluster/<name>)

variable "eks_cluster" {
  description = "The target EKS cluster name"
  type        = string
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
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "DescribeCluster"
        Effect   = "Allow"
        Action   = ["eks:DescribeCluster"]
        Resource = ["arn:aws:eks:${var.aws_default_region}:${var.aws_account_id}:cluster/${var.eks_cluster}"]
      },
    ]
  })
}

output "policy" {
  description = "The inline permissions policy JSON for the grant"
  value       = local.policy
}

variable "aws_default_region" {
  description = "Region of the EKS cluster"
  type        = string
}

variable "aws_account_id" {
  description = "Account of the EKS cluster; builds the trust principal"
  type        = string
}

variable "eks_cluster" {
  description = "EKS cluster name (the access target name)"
  type        = string
}

variable "grant_id" {
  description = "The grant id, 32 lowercase hex; names the role"
  type        = string
}

variable "grantee_owner_id" {
  description = "The grantee's owner id; the trust policy's sts:SourceIdentity"
  type        = string
}

variable "level" {
  description = "The grant's EKS access level: view, edit, admin or cluster_admin"
  type        = string
}

variable "end_time" {
  description = "UTC ISO 8601 end of the grant"
  type        = string
}

variable "namespaces" {
  description = "Namespaces for the namespace-scoped levels (edit, admin); unused for view and cluster_admin"
  type        = list(string)
}

variable "cloud_tags" {
  description = "Additional tags to apply to all resources as a map"
  type        = map(string)
  default     = {}
}

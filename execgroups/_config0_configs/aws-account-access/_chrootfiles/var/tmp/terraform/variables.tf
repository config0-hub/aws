variable "aws_default_region" {
  description = "Region the grant's stack runs in"
  type        = string
}

variable "aws_account_id" {
  description = "The target account; builds the trust principal"
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
  description = "The grant's account access level: read_only, view_only, power_user, admin, security_audit or billing"
  type        = string
}

variable "end_time" {
  description = "UTC ISO 8601 end of the grant"
  type        = string
}

variable "cloud_tags" {
  description = "Additional tags to apply to all resources as a map"
  type        = map(string)
  default     = {}
}

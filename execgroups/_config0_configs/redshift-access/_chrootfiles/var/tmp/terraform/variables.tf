variable "aws_default_region" {
  description = "Region of the Redshift cluster"
  type        = string
}

variable "aws_account_id" {
  description = "Account of the Redshift cluster; builds the trust principal"
  type        = string
}

variable "redshift_cluster" {
  description = "Redshift cluster identifier"
  type        = string
}

variable "db_name" {
  description = "The database the credentials log on to"
  type        = string
}

variable "db_group_names" {
  description = "Existing database groups the user joins at log on; may be empty"
  type        = list(string)
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
  description = "The grant's Redshift access level: connect"
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

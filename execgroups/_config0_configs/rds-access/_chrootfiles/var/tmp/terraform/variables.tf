variable "aws_default_region" {
  description = "Region of the DB instance or Aurora cluster"
  type        = string
}

variable "aws_account_id" {
  description = "Account of the DB instance or Aurora cluster; builds the trust principal"
  type        = string
}

variable "db_resource_id" {
  description = "The DB instance's DbiResourceId (db-...) or the Aurora cluster's DbClusterResourceId (cluster-...)"
  type        = string
}

variable "grant_id" {
  description = "The grant id, 32 lowercase hex; names the role and the database user"
  type        = string
}

variable "grantee_owner_id" {
  description = "The grantee's owner id; the trust policy's sts:SourceIdentity"
  type        = string
}

variable "level" {
  description = "The grant's RDS access level: connect, read_only or read_write"
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

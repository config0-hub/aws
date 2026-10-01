variable "aws_default_region" {
  description = "Region of the cache"
  type        = string
}

variable "aws_account_id" {
  description = "Account of the cache; builds the trust principal"
  type        = string
}

variable "cache_name" {
  description = "Replication group id or serverless cache name"
  type        = string
}

variable "cache_type" {
  description = "replication_group or serverless"
  type        = string
}

variable "user_group_id" {
  description = "The cache's existing user group the grant's user joins"
  type        = string
}

variable "engine" {
  description = "The ElastiCache user's engine: redis or valkey"
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
  description = "The grant's ElastiCache access level: read or read_write"
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

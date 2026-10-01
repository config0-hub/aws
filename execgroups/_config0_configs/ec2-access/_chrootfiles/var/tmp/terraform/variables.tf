variable "aws_default_region" {
  description = "Region of the EC2 instance"
  type        = string
}

variable "aws_account_id" {
  description = "Account of the EC2 instance; builds the trust principal"
  type        = string
}

variable "instance_id" {
  description = "EC2 instance id (the access target name)"
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
  description = "The grant's EC2 access level: session, port_forward, ssh (ec2) or rdp (ec2_windows)"
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

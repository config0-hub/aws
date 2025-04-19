variable "aws_default_region" {
  description = "The AWS region to deploy resources to"
  type        = string
  default     = "us-east-1"
}

variable "role_name" {
  description = "Name of the IAM role to be created"
  type        = string
  default     = "eval-config0-ec2"
}

variable "iam_instance_profile" {
  description = "Name of the IAM instance profile to be created"
  type        = string
  default     = "eval-config0-ec2"
}

variable "iam_role_policy_name" {
  description = "Name of the IAM role policy to be created"
  type        = string
  default     = "eval-config0-ec2"
}

variable "assume_policy" {
  description = "Base64 encoded assume role policy document for EC2 instances"
  type        = string
  default     = "ewogICJWZXJzaW9uIjogIjIwMTItMTAtMTciLAogICJTdGF0ZW1lbnQiOiBbCiAgICB7CiAgICAgICJBY3Rpb24iOiAic3RzOkFzc3VtZVJvbGUiLAogICAgICAiUHJpbmNpcGFsIjogewogICAgICAgICJTZXJ2aWNlIjogImVjMi5hbWF6b25hd3MuY29tIgogICAgICB9LAogICAgICAiRWZmZWN0IjogIkFsbG93IiwKICAgICAgIlNpZCI6ICIiCiAgICB9CiAgXQp9Cg=="
}

variable "policy" {
  description = "Base64 encoded IAM policy document defining permissions for the role"
  type        = string
  default     = "eyJWZXJzaW9uIjogIjIwMTItMTAtMTciLCAiU3RhdGVtZW50IjogW3siQWN0aW9uIjogWyJzMzoqIiwgImVjcjoqIiwgImVjMjoqIiwgInNzbToqIiwgImVrczoqIiwgInJkczoqIiwgImR5bmFtb2RiOioiXSwgIlJlc291cmNlIjogIioiLCAiRWZmZWN0IjogIkFsbG93In1dfQ=="
}

variable "cloud_tags" {
  description = "Additional tags to apply to all resources as a map"
  type        = map(string)
  default     = {}
}


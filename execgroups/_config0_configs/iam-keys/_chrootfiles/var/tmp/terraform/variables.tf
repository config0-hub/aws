variable "policy" {
  description = "Base64 encoded IAM policy document"
  type        = string
  default     = "eyJWZXJzaW9uIjogIjIwMTItMTAtMTciLCAiU3RhdGVtZW50IjogW3siQWN0aW9uIjogWyJzMzoqIiwgImVjcjoqIiwgImVjMjoqIiwgInNzbToqIiwgImVrczoqIiwgInJkczoqIiwgImR5bmFtb2RiOioiXSwgIlJlc291cmNlIjogIioiLCAiRWZmZWN0IjogIkFsbG93In1dfQ=="
}

variable "policy_name" {
  description = "Name of the IAM policy to create"
  type        = string
  default     = "eval-config0-user"
}

variable "iam_name" {
  description = "Name of the IAM user to create"
  type        = string
  default     = "test-config0-user"
}

variable "aws_default_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "cloud_tags" {
  description = "Additional tags as a map"
  type        = map(string)
  default     = {}
}
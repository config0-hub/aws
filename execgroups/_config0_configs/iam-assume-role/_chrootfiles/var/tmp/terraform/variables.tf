variable "aws_default_region" {
  type        = string
  default     = "us-east-1"
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}

variable "policy_arns" {
  type    = list
  default = [ "arn:aws:iam::aws:policy/PowerUserAccess",
              "arn:aws:iam::aws:policy/IAMFullAccess" ]
}

variable "target_account_id" {
}

variable "target_account_user" {
  default = "root"
}

variable "cross_account_rolename" {
  default = "config0-main"
}

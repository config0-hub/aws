##########################################################
# variables
##########################################################

variable "aws_default_region" {
    default = "us-east-1"
}

variable "role_name" {
    default = "eval-config0-ec2"
}

variable "iam_instance_profile" {
    default = "eval-config0-ec2"
}

variable "iam_role_policy_name" {
    default = "eval-config0-ec2"
}

variable "assume_policy" {
  default = "ewogICJWZXJzaW9uIjogIjIwMTItMTAtMTciLAogICJTdGF0ZW1lbnQiOiBbCiAgICB7CiAgICAgICJBY3Rpb24iOiAic3RzOkFzc3VtZVJvbGUiLAogICAgICAiUHJpbmNpcGFsIjogewogICAgICAgICJTZXJ2aWNlIjogImVjMi5hbWF6b25hd3MuY29tIgogICAgICB9LAogICAgICAiRWZmZWN0IjogIkFsbG93IiwKICAgICAgIlNpZCI6ICIiCiAgICB9CiAgXQp9Cg=="
}

variable "policy" {
  default = "eyJWZXJzaW9uIjogIjIwMTItMTAtMTciLCAiU3RhdGVtZW50IjogW3siQWN0aW9uIjogWyJzMzoqIiwgImVjcjoqIiwgImVjMjoqIiwgInNzbToqIiwgImVrczoqIiwgInJkczoqIiwgImR5bmFtb2RiOioiXSwgIlJlc291cmNlIjogIioiLCAiRWZmZWN0IjogIkFsbG93In1dfQ=="
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}

##########################################################
# main
##########################################################

resource "aws_iam_role" "default" {
  name = var.role_name
  assume_role_policy = base64decode(var.assume_policy)
}

resource "aws_iam_instance_profile" "default" {
  name = var.iam_instance_profile
  role = aws_iam_role.default.name
}

resource "aws_iam_role_policy" "default" {
  name = var.iam_role_policy_name
  role = aws_iam_role.default.id
  policy = base64decode(var.policy)
}



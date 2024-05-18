variable "policy_arn" {
    default = "arn:aws:iam::aws:policy/PowerUserAccess"
}

variable "aws_default_region" {
  type        = string
  default     = "eu-west-1"
}

variable "iam_name" {
    default = "eval-config0-user"
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}

###################################################################
# BELOW: Custom policy and pgp encrypted out for keys
###################################################################

#variable "pgp_key" {
#    default = "keybase:a_keybase_user"
#}

#variable "policy" {
#  default = <<EOF
#{
#  "Version": "2012-10-17",
#  "Statement": [
#    {
#      "Action": [
#          "ecr:GetAuthorizationToken",
#          "ecr:BatchCheckLayerAvailability",
#          "ecr:GetDownloadUrlForLayer",
#          "ecr:GetRepositoryPolicy",
#          "ecr:DescribeRepositories",
#          "ecr:ListImages",
#          "ecr:DescribeImages",
#          "ecr:BatchGetImage",
#          "ecr:InitiateLayerUpload",
#          "ecr:UploadLayerPart",
#          "ecr:CompleteLayerUpload",
#          "ecr:PutImage",
#          "ecr:GetLoginToken"
#      ],
#      "Effect": "Allow",
#      "Resource": "*"
#    }
#  ]
#}
#EOF
#}

#variable "policy_name" {
#    default = "ecr-ci"
#}

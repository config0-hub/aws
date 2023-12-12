#variable "policy" {
#  default = <<EOF
#{
#  "Version": "2012-10-17",
#  "Statement": [
#    {
#      "Action": [
#            "s3:*",
#            "ecr:*",
#            "ec2:*",
#            "ssm:*",
#            "eks:*",
#            "rds:*",
#            "dynamodb:*",
#        ],
#      ],
#      "Effect": "Allow",
#      "Resource": "*"
#    }
#  ]
#}
#EOF
#}

variable "policy" {
  default = "eyJWZXJzaW9uIjogIjIwMTItMTAtMTciLCAiU3RhdGVtZW50IjogW3siQWN0aW9uIjogWyJzMzoqIiwgImVjcjoqIiwgImVjMjoqIiwgInNzbToqIiwgImVrczoqIiwgInJkczoqIiwgImR5bmFtb2RiOioiXSwgIlJlc291cmNlIjogIioiLCAiRWZmZWN0IjogIkFsbG93In1dfQ=="
}

variable "policy_name" {
    default = "eval-config0-user"
}

variable "iam_name" {
    default = "test-config0-user"
}

variable "aws_default_region" {
    default  = "us-east-1"
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}


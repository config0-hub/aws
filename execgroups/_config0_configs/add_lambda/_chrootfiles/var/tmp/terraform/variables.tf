variable "product" {
  type        = string
  default     = "lambda"
}

variable "aws_default_region" {
  type        = string
  default     = "eu-west-1"
}

variable "s3_bucket" {
  type        = string
}

variable "s3_key" {
  type        = string
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}

variable "lambda_name" {
  type        = string
}

variable "handler" {
  type        = string
  default     = "app.handler"
}


variable "runtime" {
  type        = string
  default     = "python3.9"
}

variable "lambda_layers" {
  type        = string
  default     = null
}

variable "memory_size" {
  default     = 128
}

variable "lambda_timeout" {
  default     = 900
}

variable "lambda_env_vars" {
  description = "environmental variables for lambda as a map"
  type        = map(string)
  default     = {}
}

variable "assume_policy" {
  default = <<EOF
{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": "sts:AssumeRole",
     "Principal": {
       "Service": "lambda.amazonaws.com"
     },
     "Effect": "Allow",
     "Sid": ""
   }
 ]
}
EOF
}

variable "policy_template_hash" {
  default     = "ewogIlZlcnNpb24iOiAiMjAxMi0xMC0xNyIsCiAiU3RhdGVtZW50IjogWwogICB7CiAgICAgIkFjdGlvbiI6IFsKICAgICAgICJsb2dzOkNyZWF0ZUxvZ0dyb3VwIiwKICAgICAgICJsb2dzOkNyZWF0ZUxvZ1N0cmVhbSIsCiAgICAgICAibG9nczpQdXRMb2dFdmVudHMiCiAgICAgXSwKICAgICAiUmVzb3VyY2UiOiAiYXJuOmF3czpsb2dzOio6KjoqIiwKICAgICAiRWZmZWN0IjogIkFsbG93IgogICB9CiBdCn0K"
}

#####################################
# Default policy template hash below
#####################################
#{
# "Version": "2012-10-17",
# "Statement": [
#   {
#     "Action": [
#       "logs:CreateLogGroup",
#       "logs:CreateLogStream",
#       "logs:PutLogEvents"
#     ],
#     "Resource": "arn:aws:logs:*:*:*",
#     "Effect": "Allow"
#   }
# ]
#}

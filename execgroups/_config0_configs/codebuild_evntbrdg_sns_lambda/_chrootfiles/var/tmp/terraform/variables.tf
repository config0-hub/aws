variable "topic_name" {
  type        = string
  description = "The name of the SNS topic to which the build notifications will be sent"
}

variable "aws_default_region" {
  type        = string
  description = "eu-west-1"
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}

variable "lambda_name" {
  type = string
}

#variable "codebuild_name" {
#  type = string
#}


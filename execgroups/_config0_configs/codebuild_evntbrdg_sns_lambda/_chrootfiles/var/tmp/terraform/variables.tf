variable "topic_name" {
  type        = string
  description = "The name of the SNS topic to which the build notifications will be sent"
}

variable "aws_default_region" {
  type        = string
  description = "The AWS region where resources will be created (e.g., eu-west-1)"
}

variable "cloud_tags" {
  description = "Additional tags to apply to created resources"
  type        = map(string)
  default     = {}
}

variable "lambda_name" {
  type        = string
  description = "The name of the Lambda function that will process the SNS notifications"
}


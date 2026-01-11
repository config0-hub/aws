variable "product" {
  description = "Product name used for tagging"
  type        = string
  default     = "lambda"
}

variable "aws_default_region" {
  description = "AWS region where resources will be deployed"
  type        = string
  default     = "eu-west-1"
}

variable "s3_bucket" {
  description = "S3 bucket containing the Lambda deployment package"
  type        = string
}

variable "s3_key" {
  description = "S3 key path to the Lambda deployment package"
  type        = string
}

variable "cloud_tags" {
  description = "Additional tags as a map to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "lambda_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "handler" {
  description = "Lambda function handler entry point"
  type        = string
  default     = "app.handler"
}

variable "runtime" {
  description = "Lambda runtime environment"
  type        = string
  default     = "python3.11"
}

variable "lambda_layers" {
  description = "Comma-separated list of Lambda layer ARNs to attach to the function"
  type        = string
  default     = null
}

variable "memory_size" {
  description = "Amount of memory in MB allocated to the Lambda function"
  type        = number
  default     = 128
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 900
}

variable "lambda_env_vars" {
  description = "Environment variables for the Lambda function as a map"
  type        = map(string)
  default     = {}
}

variable "assume_policy" {
  description = "IAM policy allowing Lambda service to assume the role"
  type        = string
  default     = <<EOF
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
  description = "Base64 encoded IAM policy template that will be rendered with variables"
  type        = string
  default     = "ewogIlZlcnNpb24iOiAiMjAxMi0xMC0xNyIsCiAiU3RhdGVtZW50IjogWwogICB7CiAgICAgIkFjdGlvbiI6IFsKICAgICAgICJsb2dzOkNyZWF0ZUxvZ0dyb3VwIiwKICAgICAgICJsb2dzOkNyZWF0ZUxvZ1N0cmVhbSIsCiAgICAgICAibG9nczpQdXRMb2dFdmVudHMiCiAgICAgXSwKICAgICAiUmVzb3VyY2UiOiAiYXJuOmF3czpsb2dzOio6KjoqIiwKICAgICAiRWZmZWN0IjogIkFsbG93IgogICB9CiBdCn0K"
}

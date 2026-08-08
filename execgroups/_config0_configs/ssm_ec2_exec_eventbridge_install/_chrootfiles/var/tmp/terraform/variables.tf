variable "aws_region" {
  description = "AWS region for all resources. Always ap-northeast-1 for this module."
  type        = string
  default     = "ap-northeast-1"
}

variable "managed_tag_key" {
  description = "Tag key used to scope SSM SendCommand to instances this module is allowed to target."
  type        = string
  default     = "config0:managed"
}

variable "managed_tag_value" {
  description = "Tag value used to scope SSM SendCommand to instances this module is allowed to target."
  type        = string
  default     = "true"
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention for the state machine, SSM command, and Lambda log groups."
  type        = number
  default     = 30
}

variable "s3_log_expiration_days" {
  description = "Lifecycle expiration (days) for objects in the native SSM output / payload bucket."
  type        = number
  default     = 30
}

variable "lambda_timeout_seconds" {
  description = "Timeout for the starter/callback/fallback Lambdas. Bounds a single SendCommand+PutItem, a single conditional-acquire+SendTask, or one fallback scan pass — none of which is long-running."
  type        = number
  default     = 60
}

# ---------------------------------------------------------------------------
# The Lambda deployment package location. The zips are built and uploaded by
# the lambda-build order (docker-to-lambda.sh under CodeBuild); this install
# order references them by bucket + key (add_lambda pattern).
# ---------------------------------------------------------------------------

variable "s3_bucket" {
  description = "Name of the S3 bucket holding the Lambda deployment packages (created by the bucket order)."
  type        = string
}

variable "s3_key_starter" {
  description = "S3 key of the starter Lambda deployment zip."
  type        = string
}

variable "s3_key_callback" {
  description = "S3 key of the callback Lambda deployment zip."
  type        = string
}

variable "s3_key_fallback" {
  description = "S3 key of the fallback Lambda deployment zip."
  type        = string
}

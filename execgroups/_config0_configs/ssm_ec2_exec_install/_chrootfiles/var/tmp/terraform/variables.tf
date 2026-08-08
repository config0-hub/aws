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
  description = "CloudWatch Logs retention for the state machine and SSM command log groups."
  type        = number
  default     = 30
}

variable "s3_log_expiration_days" {
  description = "Lifecycle expiration (days) for objects in the native SSM output / payload bucket."
  type        = number
  default     = 30
}

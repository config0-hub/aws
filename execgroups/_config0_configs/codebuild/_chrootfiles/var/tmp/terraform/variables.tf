variable "aws_default_region" {
  type        = string
  default     = "eu-west-1"
}

variable "build_image" {
  type        = string
  default     = "aws/codebuild/standard:5.0"
}

variable "image_type" {
  type        = string
  default     = "LINUX_CONTAINER"
}

variable "s3_bucket" {
  type        = string
}

variable "s3_bucket_output" {
  type        = string
}

variable "s3_bucket_cache" {
  type        = string
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}

variable "codebuild_name" {
  type        = string
}

variable "codebuild_env_vars" {
  description = "environmental variables for codebuild"
  type        = map(string)
  default     = {}
}

variable "privileged_mode" {
  default = true
}

variable "description" {
  default = "Codebuild project"
}

variable "build_timeout" {
  default = "5"
}

variable "compute_type" {
  default = "BUILD_GENERAL1_SMALL"
}

variable "buildspec_hash" {
  type    = string
  description = "buildspec template as a base64 hash"
}

variable "aws_default_region" {
  type        = string
  default     = "eu-west-1"
}

variable "build_image" {
  type        = string
  default     = "aws/codebuild/standard:5.0"
  #default     = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
}

variable "image_type" {
  type        = string
  default     = "LINUX_CONTAINER"
}

variable "s3_bucket" {
  type        = string
}

variable "s3_bucket_cache" {
  type        = string
}

variable "s3_bucket_output" {
  type        = string
}

variable "codebuild_name" {
  type        = string
}

variable "git_url" {
  type        = string
}

variable "ssm_ssh_key" {
  type        = string
}

variable "env_vars" {
  description = "env_vars"
  type        = map(string)
  default     = {}
}

variable "privileged_mode" {
  default = true
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}


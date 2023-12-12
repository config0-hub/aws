variable "aws_default_region" {
  type        = string
  default     = "eu-west-1"
}

variable "git_repo" {
  type        = string
}

variable "git_owner" {
  type        = string
}

variable "git_branch" {
  type        = string
}

variable "code_provider" {
  type        = string
  default     = "GitHub"
}

variable "webhook_secret" {
  type        = string
}

variable "codebuild_name" {
  type        = string
}

variable "codepipeline_name" {
  type        = string
}

variable "s3_bucket" {
  type        = string
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}


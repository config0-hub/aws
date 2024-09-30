variable "aws_default_region" {
  type        = string
  default     = "eu-west-1"
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

variable "s3_src_bucket" {
  type        = string
}

variable "s3_src_key" {
  type        = string
  default     = "ci/build/build.zip"
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}


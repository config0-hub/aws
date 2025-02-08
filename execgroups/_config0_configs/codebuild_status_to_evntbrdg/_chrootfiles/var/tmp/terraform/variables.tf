variable "aws_default_region" {
  type        = string
  description = "eu-west-1"
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}

variable "codebuild_name" {
  type = string
}


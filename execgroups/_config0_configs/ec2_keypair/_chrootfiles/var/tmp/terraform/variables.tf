variable "aws_default_region" {
  type        = string
  description = "us-east-2"
}

variable "key_name" {
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}


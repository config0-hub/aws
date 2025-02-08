variable "aws_default_region" {
  type        = string
  description = "eu-west-1"
}

variable "key_name" {}
variable "public_key" {}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}


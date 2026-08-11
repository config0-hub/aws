variable "key_name" {
  description = "Name of the generated EC2 key pair."
  type        = string
}

variable "aws_default_region" {
  description = "AWS region for the EC2 key pair."
  type        = string
  default     = "ap-northeast-1"
}

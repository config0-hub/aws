variable "key_name" {
  description = "Name of the EC2 key pair. EC2 key pair names are unique per account and region."
  type        = string
}

variable "aws_default_region" {
  description = "AWS region of the key pair and of its SSM parameter."
  type        = string
}

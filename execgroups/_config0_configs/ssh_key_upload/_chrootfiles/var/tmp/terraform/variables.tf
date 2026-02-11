variable "aws_default_region" {
  type        = string
  description = "The AWS region to deploy resources (e.g., eu-west-1)"
}

variable "key_name" {
  type        = string
  description = "Name for the AWS key pair to be created"
}

variable "public_key" {
  type        = string
  description = "Base64 encoded public key material to import"
  sensitive   = true
}

variable "cloud_tags" {
  description = "Additional tags as a map"
  type        = map(string)
  default     = {}
}

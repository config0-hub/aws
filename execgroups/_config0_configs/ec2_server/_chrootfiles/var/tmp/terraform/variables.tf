variable "hostname" {}
variable "ssh_key_name" {}

variable "aws_default_region" {
  default = "us-east-2"
}

variable "ami" {
  default = "ami-055750c183ca68c38"
}

variable "associate_public_ip_address" {
  default     = true
}

variable "instance_type" {
  default     = "t3.micro"
}

variable "disktype" {
  default     = "gp2"
}

variable "disksize" {
  default     = "20"
}

# this should be b64 encoded
variable "user_data" {
  default = null
}

variable "ami_filter" {
  default = "ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"
}

variable "ami_owner" {
  default = "099720109477" # Canonical
}

variable "iam_instance_profile" {
  default = null
}

variable "subnet_id" {
  default = null
}

variable "security_group_ids" {
  default = null
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}


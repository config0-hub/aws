# Input variables
variable "hostname" {
  description = "Hostname for the EC2 instance, used in Name tag"
  type        = string
}

variable "ssh_key_name" {
  description = "Name of the SSH key pair to use for the instance"
  type        = string
}

variable "aws_default_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-2"
}

variable "ami" {
  description = "Default AMI ID to use if not using the AMI data source"
  type        = string
  default     = "ami-055750c183ca68c38"
}

variable "associate_public_ip_address" {
  description = "Whether to associate a public IP address with the instance"
  type        = bool
  default     = true
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "disktype" {
  description = "EBS volume type for the root block device"
  type        = string
  default     = "gp2"
}

variable "disksize" {
  description = "Size of the root EBS volume in GB"
  type        = number
  default     = 20
}

variable "user_data" {
  description = "Base64 encoded user data to provide when launching the instance"
  type        = string
  default     = null
}

variable "ami_filter" {
  description = "Filter pattern to locate specific AMI"
  type        = string
  default     = "ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"
}

variable "ami_owner" {
  description = "AWS account ID of the AMI owner (Canonical for Ubuntu)"
  type        = string
  default     = "099720109477" # Canonical
}

variable "iam_instance_profile" {
  description = "IAM instance profile to attach to the instance"
  type        = string
  default     = null
}

variable "subnet_id" {
  description = "VPC Subnet ID to launch the instance in"
  type        = string
  default     = null
}

variable "security_group_ids" {
  description = "Comma-separated list of security group IDs to associate with the instance"
  type        = string
  default     = null
}

variable "cloud_tags" {
  description = "Additional tags as a map to apply to all resources"
  type        = map(string)
  default     = {}
}
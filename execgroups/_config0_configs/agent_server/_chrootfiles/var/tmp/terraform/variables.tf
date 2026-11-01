variable "hostname" {
  description = "The server's hostname; also names its role, instance profile, security group and queue"
  type        = string
}

variable "aws_default_region" {
  description = "AWS region where resources will be created"
  type        = string
}

variable "subnet_id" {
  description = "The subnet to launch the server in; a private subnet needs a 0.0.0.0/0 route to a NAT gateway"
  type        = string
}

variable "public_subnet" {
  description = "The public-subnet option: the server gets a public address and the NAT egress check is skipped"
  type        = bool
  default     = false
}

variable "key_parameter_paths" {
  description = "Comma-delimited SSM parameter paths of the named key sets the instance may read, never a prefix"
  type        = string
}

variable "ssh_key_name" {
  description = "The key pair for the port 22 option (null: no key pair)"
  type        = string
  default     = null
}

variable "ssh_cidr" {
  description = "The CIDR allowed on port 22 for the port 22 option (null: no inbound port)"
  type        = string
  default     = null
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

variable "ami_filter" {
  description = "Filter pattern to locate specific AMI"
  type        = string
  default     = "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"
}

variable "ami_owner" {
  description = "AWS account ID of the AMI owner (Canonical for Ubuntu)"
  type        = string
  default     = "099720109477" # Canonical
}

variable "cloud_tags" {
  description = "Additional tags as a map to apply to all resources"
  type        = map(string)
  default     = {}
}

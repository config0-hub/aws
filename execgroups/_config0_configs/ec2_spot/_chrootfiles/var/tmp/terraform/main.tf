variable "aws_default_region" {
  default = "eu-west-1"
}

variable "ami" {}
variable "instance_type" {}
variable "spot_price" {}
variable "spot_type" {}
variable "hostname" {}
variable "environment" {}
variable "billing_tag" {}
variable "security_group_ids" {}
variable "subnet_id" {}
variable "key_name" {}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}

resource "aws_spot_instance_request" "default" {
  ami = var.ami
  instance_type = var.instance_type
  spot_price = var.spot_price
  wait_for_fulfillment = true
  spot_type = var.spot_type

  key_name = var.key_name
  security_groups = var.security_group_ids
  subnet_id = var.subnet_id
  associate_public_ip_address = true

  tags = {
    Name = var.hostname
    billing_tag = var.billing_tag
    environment = var.environment
    InstanceType = "spot"
  }

}

output "instance_id" {
  value = aws_spot_instance_request.default.id
}

output "spot_instance_ids" {
  value = concat(aws_spot_instance_request.default.*.spot_instance_id, [""])
}

output "public_ips" {
  value = concat(aws_spot_instance_request.default.*.public_ip, [""])
}

output "private_ips" {
  value = concat(aws_spot_instance_request.default.*.private_ip, [""])
}


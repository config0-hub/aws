# Output values
output "instance_id" {
  description = "The ID of the created EC2 instance"
  value       = aws_instance.default.id
}

output "ami" {
  description = "The AMI ID used for the instance"
  value       = aws_instance.default.ami
}

output "arn" {
  description = "The ARN of the created EC2 instance"
  value       = aws_instance.default.arn
}

output "availability_zone" {
  description = "The availability zone where the instance was created"
  value       = aws_instance.default.availability_zone
}

output "private_dns" {
  description = "The private DNS name of the instance"
  value       = aws_instance.default.private_dns
}

output "private_ip" {
  description = "The private IP address of the instance"
  value       = aws_instance.default.private_ip
}

output "public_dns" {
  description = "The public DNS name of the instance"
  value       = aws_instance.default.public_dns
}

output "public_ip" {
  description = "The public IP address of the instance"
  value       = aws_instance.default.public_ip
}

# SSM target identity facts — the host-order seam resolves the server record
# and validates account/region/instance-id/profile/managed tag from it.

output "account_id" {
  description = "AWS account id the instance was created in"
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "AWS region the instance was created in"
  value       = data.aws_region.current.name
}

output "instance_profile" {
  description = "IAM instance profile attached to the instance (null when none)"
  value       = aws_instance.default.iam_instance_profile
}

output "managed_tag_key" {
  description = "Managed tag key applied for SSM SendCommand targeting (null when none)"
  value       = var.managed_tag_key
}

output "managed_tag_value" {
  description = "Managed tag value applied for SSM SendCommand targeting (null when none)"
  value       = var.managed_tag_value
}


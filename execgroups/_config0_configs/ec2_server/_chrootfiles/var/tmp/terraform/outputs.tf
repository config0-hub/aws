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


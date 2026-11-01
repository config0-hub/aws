# The server record's ids, as the ec2_server execgroup outputs them, and the
# server's own queue URL beside them.

output "instance_id" {
  description = "The ID of the created EC2 instance"
  value       = aws_instance.server.id
}

output "private_ip" {
  description = "The private IP address of the instance"
  value       = aws_instance.server.private_ip
}

output "public_ip" {
  description = "The public IP address of the instance (empty without the public-subnet option)"
  value       = aws_instance.server.public_ip
}

output "account_id" {
  description = "AWS account id the instance was created in"
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "AWS region the instance was created in"
  value       = data.aws_region.current.name
}

output "instance_profile" {
  description = "IAM instance profile attached to the instance"
  value       = aws_instance.server.iam_instance_profile
}

output "iam_role_arn" {
  description = "The instance role, the identity the server acts as"
  value       = aws_iam_role.server.arn
}

output "queue_url" {
  description = "The server's own SQS queue"
  value       = aws_sqs_queue.server.url
}

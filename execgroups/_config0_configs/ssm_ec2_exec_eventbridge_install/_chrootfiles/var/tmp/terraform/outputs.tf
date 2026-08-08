output "state_machine_arn" {
  description = "ARN of the ssm_ec2_exec_eventbridge Standard state machine."
  value       = aws_sfn_state_machine.ssm_ec2_exec_eventbridge.arn
}

output "bucket_name" {
  description = "Name of the S3 bucket used for SSM native command output and payload staging."
  value       = aws_s3_bucket.logs.bucket
}

output "instance_profile_name" {
  description = "Name of the shared instance profile to attach to EC2 targets managed by this module."
  value       = aws_iam_instance_profile.instance.name
}

output "dynamodb_table_name" {
  description = "Name of the token-map table keyed by SSM CommandId."
  value       = aws_dynamodb_table.tokens.name
}

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

# ---------------------------------------------------------------------------
# Discovery contract for the host-order seam: the install resource record is
# the single source for the state machine ARN, the payload bucket + key
# layout, the instance profile name, the canonical managed tag, and the SOPS
# KMS key ARN. Everything below is promoted onto the install record.
# ---------------------------------------------------------------------------

output "kms_key_arn" {
  description = "ARN of the KMS key sealing the SOPS host-configuration payload."
  value       = aws_kms_key.sops.arn
}

output "managed_tag_key" {
  description = "Canonical tag key an EC2 target must carry to be SendCommand-targetable."
  value       = var.managed_tag_key
}

output "managed_tag_value" {
  description = "Canonical tag value an EC2 target must carry to be SendCommand-targetable."
  value       = var.managed_tag_value
}

output "payload_key_layout" {
  description = "Key layout inside bucket_name a host-configuration fire uses: payload read, manifest/log writes. Matches the instance role's scoped grants (iam.tf)."
  value       = "<date>/<run-id>/attempt-<n>/{payload,manifest.json,stdout.log,stderr.log}"
}

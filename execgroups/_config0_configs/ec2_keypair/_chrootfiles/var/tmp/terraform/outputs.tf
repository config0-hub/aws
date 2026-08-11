output "key_name" {
  description = "Generated EC2 key pair name."
  value       = aws_key_pair.generated.key_name
}

output "key_pair_id" {
  description = "Generated EC2 key pair ID."
  value       = aws_key_pair.generated.key_pair_id
}

output "fingerprint" {
  description = "Fingerprint of the generated EC2 key pair."
  value       = aws_key_pair.generated.fingerprint
}

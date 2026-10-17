output "key_name" {
  description = "Name of the EC2 key pair."
  value       = awscc_ec2_key_pair.this.key_name
}

output "key_pair_id" {
  description = "ID of the EC2 key pair."
  value       = awscc_ec2_key_pair.this.key_pair_id
}

output "public_key" {
  description = "Public half of the key pair, in OpenSSH format."
  value       = data.aws_key_pair.this.public_key
}

output "private_key_ssm_path" {
  description = "Name of the SSM parameter where AWS keeps the private half. A name, not the key."
  value       = "/ec2/keypair/${awscc_ec2_key_pair.this.key_pair_id}"
}

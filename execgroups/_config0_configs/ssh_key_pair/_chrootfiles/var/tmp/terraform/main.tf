# EC2 makes the key pair. With no public_key_material, AWS generates the pair,
# keeps the private half in SSM Parameter Store at /ec2/keypair/<key_pair_id>
# and deletes that parameter with the key pair. No state, output or row holds
# the private half.
resource "awscc_ec2_key_pair" "this" {
  key_name = var.key_name
  key_type = "rsa"

  # Every property is create-only, tags included: a changed tag replaces the
  # key pair, and with it the private half. The tags stay fixed.
  tags = [
    { key = "ManagedBy", value = "config0" },
    { key = "Component", value = "ssh-key-pair" },
  ]
}

# The public half, read back from EC2.
data "aws_key_pair" "this" {
  key_pair_id        = awscc_ec2_key_pair.this.key_pair_id
  include_public_key = true
}

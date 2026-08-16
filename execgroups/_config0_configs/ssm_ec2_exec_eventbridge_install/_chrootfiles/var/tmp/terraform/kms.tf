# ---------------------------------------------------------------------------
# One target-account KMS key sealing the SOPS host-configuration payload.
#
# Resolve-or-create: this install is the single owner of its own per-install
# SOPS seal key (alias scoped by install_name) in a target account. Terraform
# creates it once under a fixed alias; every later apply of the same install
# resolves it from state. A pre-existing alias created outside this stack
# fails the apply loud instead of silently adopting a key with an unknown
# policy.
#
# The target-bound handler encrypts secrets.enc.json against this key ARN
# (promoted on the install resource record); the instance role gets decrypt on
# this ARN only (iam.tf).
# ---------------------------------------------------------------------------

resource "aws_kms_key" "sops" {
  description             = "SOPS seal key for Config0 SSM host-configuration payloads"
  enable_key_rotation     = true
  deletion_window_in_days = 7

  tags = local.tags
}

resource "aws_kms_alias" "sops" {
  name          = "alias/${local.name_prefix}-sops"
  target_key_id = aws_kms_key.sops.key_id
}

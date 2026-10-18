# ---------------------------------------------------------------------------
# The database grant scripts (rds-access-user, db-password-access-user,
# docdb-access-user) run on hosts under the shared instance role and read a
# database's admin login on every run, from the secret where RDS or
# DocumentDB keeps the master user name and password. RDS names that secret
# rds!db-<id> for a DB instance. DocumentDB runs on the RDS management API,
# which names a cluster's secret rds!cluster-<id>; the same prefix also covers
# Aurora and Multi-AZ DB cluster secrets in this account and region, and no
# name pattern is narrower. A managed secret's name can only be created by
# the service that manages it, so this grants GetSecretValue on those two
# kinds of RDS-managed secret in this account and region, nothing else. The
# aws_rds and aws_docdb stacks leave the secret on the AWS managed key
# aws/secretsmanager, whose key policy lets any principal in the account
# decrypt through Secrets Manager (kms:ViaService), so no kms:Decrypt is
# granted here.
#
# Its own file, not iam.tf: iam.tf is byte-compared with the standalone dev101
# tree (test_ssm_eventbridge_install_parity), which runs no grant scripts.
# ---------------------------------------------------------------------------

resource "aws_iam_role_policy" "instance_rds_master_user_secret_read" {
  name = "rds-master-user-secret-read"
  role = aws_iam_role.instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadRdsMasterUserSecrets"
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${local.account_id}:secret:rds!db-*",
          "arn:aws:secretsmanager:${var.aws_region}:${local.account_id}:secret:rds!cluster-*",
        ]
      }
    ]
  })
}

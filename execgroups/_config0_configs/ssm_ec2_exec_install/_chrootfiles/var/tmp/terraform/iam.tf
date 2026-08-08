# ---------------------------------------------------------------------------
# IAM role for the Step Functions state machine.
#
# ssm:SendCommand is scoped two ways (both required, AWS evaluates them as an
# AND across the two resource-type statements a single SendCommand call
# touches): the document (AWS-RunShellScript only) AND the target instances
# (must carry the config0:managed tag) — never Resource "*" for instances.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "sfn_exec" {
  name = "${local.name_prefix}-sfn-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "sfn_send_command" {
  name = "ssm-send-command"
  role = aws_iam_role.sfn_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "SendCommandDocument"
        Effect   = "Allow"
        Action   = ["ssm:SendCommand"]
        Resource = "arn:aws:ssm:${var.aws_region}::document/AWS-RunShellScript"
      },
      {
        Sid      = "SendCommandTaggedInstances"
        Effect   = "Allow"
        Action   = ["ssm:SendCommand"]
        Resource = "arn:aws:ec2:${var.aws_region}:${local.account_id}:instance/*"
        Condition = {
          StringEquals = {
            "ssm:resourceTag/${var.managed_tag_key}" = var.managed_tag_value
          }
        }
      }
    ]
  })
}

# F5 remediation: the task-token design only ever calls SendCommand and waits
# on the callback — it never polls GetCommandInvocation/ListCommandInvocations/
# ListCommands, so those account-wide read actions were removed. Verified by
# `aws iam simulate-principal-policy` against this role during live
# verification: SendCommand (document + tagged-instance) is allowed, the three
# removed read actions are denied, and no other action is allowed.

# waitForTaskToken integration requires the SFN role be allowed to be handed
# the task token via SendCommand's own service call — no extra IAM action is
# needed for that (it's carried in the Parameters payload we build in the
# ASL), but the state machine DOES need permission to fail/succeed its own
# tasks implicitly via the service integration, which is covered by the
# ssm:SendCommand grant above.

resource "aws_iam_role_policy" "sfn_logging" {
  name = "cloudwatch-logs-delivery"
  role = aws_iam_role.sfn_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SfnLogDelivery"
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups",
        ]
        Resource = "*"
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# Shared instance role + profile — attached to EC2 targets we own. Grants
# just enough for the SSM agent, the (Phase 2) wrapper's task-token callback,
# and S3 access to the payload/output bucket.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "instance" {
  name = "${local.name_prefix}-instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "instance_ssm_core" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "instance_task_token_callback" {
  name = "sfn-task-token-callback"
  role = aws_iam_role.instance.id

  # F1 remediation: SendTaskSuccess/SendTaskFailure are bearer-token APIs —
  # the token itself is the authorization, and AWS does not support scoping
  # these two actions to a state-machine/execution ARN (confirmed live: a
  # state-machine-scoped Resource made every callback fail AccessDenied).
  # Resource must be "*". SendTaskHeartbeat is dropped — the wrapper never
  # calls it (task-token wait relies on TimeoutSecondsPath, not heartbeats).
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SendTaskOutcome"
        Effect = "Allow"
        Action = [
          "states:SendTaskSuccess",
          "states:SendTaskFailure",
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "instance_bucket_access" {
  name = "payload-and-output-bucket"
  role = aws_iam_role.instance.id

  # F3 remediation: scoped to the explicit prefixes the protocol actually
  # uses instead of bucket/* — payload reads and manifest writes live under
  # <date>/<run-id>/attempt-<n>/{payload,manifest.json} (Phase 2 CLI/wrapper
  # layout), native SSM output lives under native-output/ (the ASL
  # OutputS3KeyPrefix). ListBucket removed: every access is by known key, so
  # it was not required by the protocol.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadPayloadPrefix"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.logs.arn}/*/*/attempt-*/payload"
      },
      {
        Sid      = "WriteRunManifest"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.logs.arn}/*/*/attempt-*/manifest.json"
      },
      {
        # F2 remediation: the wrapper uploads the real stdout/stderr streams
        # it captures locally, not just the manifest.
        Sid      = "WriteRunLogs"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = [
          "${aws_s3_bucket.logs.arn}/*/*/attempt-*/stdout.log",
          "${aws_s3_bucket.logs.arn}/*/*/attempt-*/stderr.log",
        ]
      },
      {
        Sid      = "WriteNativeOutput"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.logs.arn}/native-output/*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "instance_ssm_output_logs" {
  name = "ssm-output-log-delivery"
  role = aws_iam_role.instance.id

  # F2 remediation: CloudWatchOutputConfig in the ASL SendCommand call points
  # the SSM agent at this log group, but the agent runs under the instance
  # role and had no permission to deliver to it — streams never got created.
  # CreateLogStream/PutLogEvents/CreateLogGroup need the explicit
  # log-stream-level resource (a bare trailing ":*" only matches within one
  # ARN field, not the ":log-stream:<name>" suffix those actions require —
  # confirmed via simulate-principal-policy during live verification). The
  # SSM agent also unconditionally calls CreateLogGroup as an idempotent
  # ensure-exists before writing, even though the group is pre-created here
  # by aws_cloudwatch_log_group.ssm — confirmed from a live AccessDenied in
  # amazon-ssm-agent.log ("not authorized to perform: logs:CreateLogGroup on
  # resource: .../log-group:/ssm/ssm_ec2_exec:log-stream:") on the same
  # instance role before this permission was added.
  # DescribeLogStreams stays group-scoped since it targets the group itself.
  # DescribeLogGroups is called first as part of the same ensure-exists check
  # and (per AWS) only supports Resource "*" — it can't be scoped to one log
  # group ARN, confirmed by a live AccessDenied against the scoped ARN this
  # statement used to have.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "SsmOutputLogGroupsList"
        Effect   = "Allow"
        Action   = ["logs:DescribeLogGroups"]
        Resource = "*"
      },
      {
        Sid    = "SsmOutputLogStreamDelivery"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.ssm.arn}:log-stream:*"
      },
      {
        Sid      = "SsmOutputLogGroupDescribe"
        Effect   = "Allow"
        Action   = ["logs:DescribeLogStreams"]
        Resource = "${aws_cloudwatch_log_group.ssm.arn}:*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "instance" {
  name = "${local.name_prefix}-instance"
  role = aws_iam_role.instance.name

  tags = local.tags
}

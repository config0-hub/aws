# ---------------------------------------------------------------------------
# Five roles: the Step Functions execution role, one role per Lambda
# (starter / callback / fallback), and the shared instance role/profile for
# EC2 targets.
#
# The v2 delta from v1: the SFN role no longer holds ssm:SendCommand (the
# starter Lambda sends commands), and the instance role no longer holds
# states:SendTask* (the token stays server-side — the whole point of v2). The
# ssm:SendCommand scope moves onto the starter role, kept exactly two ways
# (AWS ANDs the two resource-type statements a single SendCommand touches):
# the document (AWS-RunShellScript only) AND the target instances (must carry
# the config0:managed tag) — never Resource "*" for instances.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# --- Step Functions execution role -----------------------------------------

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

resource "aws_iam_role_policy" "sfn_invoke_starter" {
  name = "invoke-starter-lambda"
  role = aws_iam_role.sfn_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "InvokeStarter"
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = aws_lambda_function.starter.arn
      },
      {
        Sid      = "GetCommandMapping"
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem"]
        Resource = aws_dynamodb_table.tokens.arn
      },
      {
        Sid    = "InspectOrCancelTimedOutCommand"
        Effect = "Allow"
        Action = [
          "ssm:GetCommandInvocation",
          "ssm:CancelCommand",
        ]
        Resource = "*"
      }
    ]
  })
}

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

# --- Starter Lambda role ----------------------------------------------------

resource "aws_iam_role" "starter" {
  name               = "${local.name_prefix}-starter"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy" "starter" {
  name = "starter"
  role = aws_iam_role.starter.id

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
      },
      {
        Sid      = "PutToken"
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem"]
        Resource = aws_dynamodb_table.tokens.arn
      },
      {
        # SendTaskFailure is a bearer-token API — the token itself is the
        # authorization, and AWS does not support scoping it to a
        # state-machine/execution ARN, so Resource must be "*". The starter
        # calls it only on its own failure path, to release the token it
        # holds before the SFN task would otherwise hang to its timeout.
        Sid      = "FailTaskOnStarterError"
        Effect   = "Allow"
        Action   = ["states:SendTaskFailure"]
        Resource = "*"
      },
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.starter.arn}:*"
      }
    ]
  })
}

# --- Callback Lambda role ---------------------------------------------------

resource "aws_iam_role" "callback" {
  name               = "${local.name_prefix}-callback"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy" "callback" {
  name = "callback"
  role = aws_iam_role.callback.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "TokenRecord"
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.tokens.arn
      },
      {
        Sid      = "ReadCommandResult"
        Effect   = "Allow"
        Action   = ["ssm:GetCommandInvocation"]
        Resource = "*"
      },
      {
        # Bearer-token APIs — Resource must be "*" (see the starter role).
        Sid      = "CompleteTask"
        Effect   = "Allow"
        Action   = ["states:SendTaskSuccess", "states:SendTaskFailure"]
        Resource = "*"
      },
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.callback.arn}:*"
      }
    ]
  })
}

# --- Fallback Lambda role ---------------------------------------------------

resource "aws_iam_role" "fallback" {
  name               = "${local.name_prefix}-fallback"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy" "fallback" {
  name = "fallback"
  role = aws_iam_role.fallback.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "TokenRecords"
        Effect   = "Allow"
        Action   = ["dynamodb:Scan", "dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.tokens.arn
      },
      {
        Sid    = "ReadOrCancelCommand"
        Effect = "Allow"
        Action = [
          "ssm:GetCommandInvocation",
          "ssm:CancelCommand",
        ]
        Resource = "*"
      },
      {
        # Bearer-token APIs — Resource must be "*" (see the starter role).
        Sid      = "CompleteTask"
        Effect   = "Allow"
        Action   = ["states:SendTaskSuccess", "states:SendTaskFailure"]
        Resource = "*"
      },
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.fallback.arn}:*"
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# Shared instance role + profile — attached to EC2 targets we own. Grants just
# enough for the SSM agent and S3 access to the payload/output bucket. In v2
# the box no longer needs states:SendTask* — the token stays server-side.
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

resource "aws_iam_role_policy" "instance_bucket_access" {
  name = "payload-and-output-bucket"
  role = aws_iam_role.instance.id

  # Scoped to the explicit prefixes the protocol uses instead of bucket/* —
  # payload reads and manifest/stream writes live under
  # <date>/<run-id>/attempt-<n>/{payload,manifest.json,stdout.log,stderr.log},
  # native SSM output lives under native-output/. Every access is by known
  # key, so no ListBucket is required.
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
        Sid    = "WriteRunLogs"
        Effect = "Allow"
        Action = ["s3:PutObject"]
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

  # CloudWatchOutputConfig in the starter's SendCommand call points the SSM
  # agent at this log group, but the agent runs under the instance role and
  # needs permission to deliver to it. CreateLogGroup/CreateLogStream/
  # PutLogEvents need the log-stream-level resource; DescribeLogGroups only
  # supports Resource "*" (it can't be scoped to one group ARN).
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

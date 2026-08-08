# ---------------------------------------------------------------------------
# The three Lambdas. Their zips are produced by the lambda-build order (the
# ssm_ec2_exec_eventbridge_lambda_build execgroup runs docker-to-lambda.sh
# under CodeBuild and uploads starter/callback/fallback.zip to the dedicated
# artifacts bucket under an execution-scoped key prefix). This install order
# references those objects by s3_bucket + s3_key — the add_lambda pattern
# (var.s3_bucket / var.s3_key_*, no aws_s3_object, no local file, no
# source_code_hash). Terraform sees a changed s3_key when a fresh build lands
# under a new prefix and rolls the new code out to the function.
#
# Env vars are passed here and read fail-fast with os.environ[...] in the
# handlers. AWS_REGION is a reserved Lambda key the runtime sets itself, so it
# is NOT set here — the handlers read it from the runtime environment.
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "starter" {
  function_name = local.starter_function_name
  role          = aws_iam_role.starter.arn
  runtime       = "python3.12"
  handler       = "handler.handler"
  s3_bucket     = var.s3_bucket
  s3_key        = var.s3_key_starter
  timeout       = var.lambda_timeout_seconds

  environment {
    variables = {
      TOKEN_TABLE        = aws_dynamodb_table.tokens.name
      OUTPUT_BUCKET      = aws_s3_bucket.logs.bucket
      SSM_LOG_GROUP_NAME = local.ssm_log_group_name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.starter,
  ]

  tags = local.tags
}

resource "aws_lambda_function" "callback" {
  function_name = local.callback_function_name
  role          = aws_iam_role.callback.arn
  runtime       = "python3.12"
  handler       = "handler.handler"
  s3_bucket     = var.s3_bucket
  s3_key        = var.s3_key_callback
  timeout       = var.lambda_timeout_seconds

  environment {
    variables = {
      TOKEN_TABLE = aws_dynamodb_table.tokens.name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.callback,
  ]

  tags = local.tags
}

resource "aws_lambda_function" "fallback" {
  function_name = local.fallback_function_name
  role          = aws_iam_role.fallback.arn
  runtime       = "python3.12"
  handler       = "handler.handler"
  s3_bucket     = var.s3_bucket
  s3_key        = var.s3_key_fallback
  timeout       = var.lambda_timeout_seconds

  environment {
    variables = {
      TOKEN_TABLE = aws_dynamodb_table.tokens.name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.fallback,
  ]

  tags = local.tags
}

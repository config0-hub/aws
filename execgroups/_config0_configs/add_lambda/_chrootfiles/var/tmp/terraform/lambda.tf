resource "aws_lambda_function" "default" {
  function_name = var.lambda_name
  layers        = var.lambda_layers != null ? split(",", var.lambda_layers) : []
  timeout       = var.lambda_timeout
  memory_size   = var.memory_size
  s3_bucket     = var.s3_bucket
  s3_key        = var.s3_key
  role          = aws_iam_role.lambda.arn
  handler       = var.handler
  runtime       = var.runtime
  publish       = true
  depends_on    = [aws_iam_role_policy_attachment.default]

  dynamic "environment" {
    for_each = length(var.lambda_env_vars) > 0 ? [true] : []

    content {
      variables = var.lambda_env_vars
    }
  }

  tags = local.all_tags
}


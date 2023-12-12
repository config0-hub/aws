data "aws_caller_identity" "current" {}


data "template_file" "policy" {
  template = base64decode(var.policy_template_hash)
  vars = {
      aws_default_region=var.aws_default_region
      aws_account_id=data.aws_caller_identity.current.account_id
  }
}

resource "aws_iam_role" "lambda" {
  name   = "${var.lambda_name}-lambda-role"
  assume_role_policy = var.assume_policy
}

resource "aws_iam_policy" "lambda" {
  name   = "${var.lambda_name}-lambda-iam-policy"
  path         = "/"
  description  = "Policy for Lambda Role ${var.lambda_name}-lambda-role"
  policy = data.template_file.policy.rendered
}
 
resource "aws_iam_role_policy_attachment" "default" {
  role        = aws_iam_role.lambda.name
  policy_arn  = aws_iam_policy.lambda.arn
}
 
resource "aws_lambda_function" "default" {
  function_name                  = var.lambda_name
  layers                         = var.lambda_layers != null ? split(",",var.lambda_layers) : []
  memory_size                    = var.memory_size
  timeout                        = var.lambda_timeout
  s3_bucket                      = var.s3_bucket
  s3_key                         = var.s3_key
  role                           = aws_iam_role.lambda.arn
  handler                        = var.handler
  runtime                        = var.runtime
  publish                        = "true"
  depends_on                     = [aws_iam_role_policy_attachment.default]
  
  dynamic "environment" {
    for_each = length(var.lambda_env_vars) > 0 ? [true] : []

    content {
      variables = var.lambda_env_vars
    }
  }

  tags = merge(
    var.cloud_tags,
    {
      Product = var.product
    },
  )

}


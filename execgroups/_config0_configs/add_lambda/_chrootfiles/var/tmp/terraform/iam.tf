resource "aws_iam_role" "lambda" {
  name               = "${var.lambda_name}-lambda-role"
  assume_role_policy = var.assume_policy
}

resource "aws_iam_policy" "lambda" {
  name        = "${var.lambda_name}-lambda-iam-policy"
  path        = "/"
  description = "Policy for Lambda Role ${var.lambda_name}-lambda-role"
  policy      = data.template_file.policy.rendered
}

resource "aws_iam_role_policy_attachment" "default" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda.arn
}


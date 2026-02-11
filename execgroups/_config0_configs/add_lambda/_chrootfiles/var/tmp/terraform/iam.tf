resource "aws_iam_role" "lambda" {
  name               = "${var.lambda_name}-lambda-role"
  assume_role_policy = var.assume_policy
}


# Decode and render the policy template with variable substitution
locals {
  policy_decoded = base64decode(var.policy_template_hash)

  # Apply variable substitutions
  policy_rendered = replace(
    replace(
      local.policy_decoded,
      "$${aws_default_region}", var.aws_default_region
    ),
    "$${aws_account_id}", data.aws_caller_identity.current.account_id
  )
}

resource "aws_iam_policy" "lambda" {
  name        = "${var.lambda_name}-lambda-iam-policy"
  path        = "/"
  description = "Policy for Lambda Role ${var.lambda_name}-lambda-role"
  policy      = local.policy_rendered
}

resource "aws_iam_role_policy_attachment" "default" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda.arn
}





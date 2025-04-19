resource "aws_iam_role" "default" {
  name               = var.role_name
  assume_role_policy = base64decode(var.assume_policy)

  tags = var.cloud_tags
}

resource "aws_iam_instance_profile" "default" {
  name = var.iam_instance_profile
  role = aws_iam_role.default.name

  tags = var.cloud_tags
}

resource "aws_iam_role_policy" "default" {
  name   = var.iam_role_policy_name
  role   = aws_iam_role.default.id
  policy = base64decode(var.policy)
}
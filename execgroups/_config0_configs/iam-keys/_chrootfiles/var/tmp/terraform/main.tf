resource "aws_iam_user" "default" {
  name = var.iam_name
  path = "/system/"
}

resource "aws_iam_access_key" "default" {
  user    = aws_iam_user.default.name
}

resource "aws_iam_user_policy_attachment" "attachment" {
  user       = aws_iam_user.default.name
  policy_arn = aws_iam_policy.default.arn
}

resource "aws_iam_policy" "default" {
  name = var.policy_name
  policy = base64decode(var.policy)
}

#output "AWS_ACCESS_KEY_ID" {
#  value = aws_iam_access_key.default.id
#}
#
#output "AWS_SECRET_ACCESS_KEY" {
#  value = aws_iam_access_key.default.secret
#}
#


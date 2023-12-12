resource "aws_iam_user" "default" {
  name = var.iam_name
  path = "/system/"
}

resource "aws_iam_access_key" "default" {
  user    = aws_iam_user.default.name
}

resource "aws_iam_user_policy_attachment" "attachment" {
  user       = aws_iam_user.default.name
  policy_arn = var.policy_arn
}

#output "AWS_ACCESS_KEY_ID" {
#  value = aws_iam_access_key.default.id
#}
#
#output "AWS_SECRET_ACCESS_KEY" {
#  value = aws_iam_access_key.default.secret
#}
#

###################################################################
# BELOW: Custom policy and pgp encrypted out for keys
###################################################################

#output "aws_secret_access_key" {
#  value = aws_iam_access_key.default.encrypted_secret
#}

#resource "aws_iam_access_key" "default" {
#  user    = aws_iam_user.default.name
#  pgp_key = var.pgp_key
#}

#resource "aws_iam_user_policy" "default" {
#  name = var.policy_name
#  user = aws_iam_user.default.name
#  policy = var.policy
#}


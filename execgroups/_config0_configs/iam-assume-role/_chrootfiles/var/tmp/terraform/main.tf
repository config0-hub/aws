resource "aws_iam_role" "cross_account_role" {
  name = var.cross_account_rolename
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${var.target_account_id}:${var.target_account_user}"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

# Then parse through the list using count
resource "aws_iam_role_policy_attachment" "cross_account_role_attachment" {
  role       = aws_iam_role.cross_account_role.name
  count      = "${length(var.policy_arns)}"
  policy_arn = "${var.policy_arns[count.index]}"
}

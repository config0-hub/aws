resource "aws_key_pair" "default" {
  key_name   = var.key_name
  public_key = base64decode(var.public_key)
}


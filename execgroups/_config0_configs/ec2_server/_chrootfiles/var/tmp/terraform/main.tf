# EC2 Instance resource
resource "aws_instance" "default" {
  ami                         = data.aws_ami.default.id
  instance_type               = var.instance_type
  associate_public_ip_address = var.associate_public_ip_address
  key_name                    = var.ssh_key_name

  subnet_id              = var.subnet_id
  vpc_security_group_ids = var.security_group_ids != null ? split(",", var.security_group_ids) : null
  user_data              = var.user_data

  root_block_device {
    delete_on_termination = true
    volume_size           = var.disksize
    volume_type           = var.disktype
  }

  iam_instance_profile = var.iam_instance_profile

  tags = merge(
    var.cloud_tags,
    {
      Name    = var.hostname
      Product = "ec2"
    },
  )
}


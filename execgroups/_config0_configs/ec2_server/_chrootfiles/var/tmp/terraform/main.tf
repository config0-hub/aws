data "aws_ami" "default" {
  most_recent = true
  owners = [ var.ami_owner ]
  
    filter {
        name   = "name"
        values = [ var.ami_filter]
    }
  
    filter {
        name   = "virtualization-type"
        values = ["hvm"]
    }
}

resource "aws_instance" "default" {
  ami                         = data.aws_ami.default.id
  instance_type               = var.instance_type
  associate_public_ip_address = var.associate_public_ip_address
  key_name                    = var.ssh_key_name

  subnet_id = var.subnet_id != null ? var.subnet_id : null
  vpc_security_group_ids = var.security_group_ids != null ? split(",",var.security_group_ids) : null
  user_data = var.user_data != null ? var.user_data : null

  root_block_device {
    delete_on_termination = true
    volume_size = var.disksize != null ? var.disksize : null
    volume_type = var.disktype != null ? var.disktype : null
  }

  iam_instance_profile = var.iam_instance_profile != null ? var.iam_instance_profile : null

  tags = merge(
    var.cloud_tags,
    {
      Name      = var.hostname
      Product   = "ec2"
    },
  )
}

output "instance_id" {
  value = aws_instance.default.id
}
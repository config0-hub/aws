# One agent server (provisional) and its own SQS queue. Reached over Session
# Manager by default: no inbound port, no key pair, no public address. The
# instance role gets the Session Manager channel actions alone, never
# AmazonSSMManagedInstanceCore, which allows ssm:GetParameter on every
# parameter and would void the named-set fence.

locals {
  name = "agent-server-${var.hostname}"

  # The named key sets only, never the input-variable prefix. The region is a
  # wildcard, as aws-account-access names the /config0 parameters.
  key_parameter_arns = [
    for path in split(",", var.key_parameter_paths) :
    "arn:aws:ssm:*:${data.aws_caller_identity.current.account_id}:parameter${path}"
  ]
}

resource "aws_iam_role" "server" {
  name = local.name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "ec2.amazonaws.com" }
        Action    = "sts:AssumeRole"
      },
    ]
  })

  tags = var.cloud_tags
}

# Installed as written and never expanded later.
resource "aws_iam_role_policy" "server" {
  name = local.name
  role = aws_iam_role.server.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SessionManagerChannels"
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel",
          "ssm:UpdateInstanceInformation",
        ]
        Resource = "*"
      },
      {
        Sid      = "ReadNamedKeySets"
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = local.key_parameter_arns
      },
      {
        Sid      = "ReceiveOwnQueue"
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage"]
        Resource = aws_sqs_queue.server.arn
      },
    ]
  })
}

resource "aws_iam_instance_profile" "server" {
  name = local.name
  role = aws_iam_role.server.name

  tags = var.cloud_tags
}

resource "aws_security_group" "server" {
  name        = local.name
  description = "agent_server ${var.hostname}: inbound only on port 22 from ssh_cidr, when set"
  vpc_id      = data.aws_subnet.server.vpc_id

  dynamic "ingress" {
    for_each = var.ssh_cidr == null ? [] : [var.ssh_cidr]
    content {
      description = "The port 22 option"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  # Outbound only: Session Manager, the queue and saas-api.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.cloud_tags, { Name = local.name })
}

resource "aws_sqs_queue" "server" {
  name = local.name

  tags = var.cloud_tags
}

resource "aws_instance" "server" {
  ami                         = data.aws_ami.default.id
  instance_type               = var.instance_type
  associate_public_ip_address = var.public_subnet
  key_name                    = var.ssh_key_name

  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.server.id]
  iam_instance_profile   = aws_iam_instance_profile.server.name

  root_block_device {
    delete_on_termination = true
    volume_size           = var.disksize
    volume_type           = var.disktype
  }

  tags = merge(
    var.cloud_tags,
    {
      Name    = var.hostname
      Product = "agent_server"
    },
  )

  lifecycle {
    precondition {
      condition     = var.public_subnet || length(local.nat_egress_routes) > 0
      error_message = "Subnet ${var.subnet_id} has no NAT egress: its route table ${data.aws_route_table.server.route_table_id} has no 0.0.0.0/0 default route to a NAT gateway, NAT instance or other egress target (an internet gateway route does not count for a private subnet). Config0 creates no NAT gateway. Add NAT egress to the VPC's routing, or choose a public subnet with the public-subnet option."
    }
  }
}

# One agent server (provisional) and its own SQS queue. Reached over Session
# Manager by default: no inbound port, no key pair, no public address. The
# instance role gets the Session Manager channel actions alone, never
# AmazonSSMManagedInstanceCore, which allows ssm:GetParameter on every
# parameter and would void the named-set fence.

locals {
  name = "agent-server-${var.hostname}"

  # The named sets only, never the input-variable prefix: the key sets, and
  # tailscale_join with Tailscale on, never tailscale_admin. The region is a
  # wildcard, as aws-account-access names the /config0 parameters.
  key_parameter_arns = [
    for path in split(",", var.key_parameter_paths) :
    "arn:aws:ssm:*:${data.aws_caller_identity.current.account_id}:parameter${path}"
  ]

  # s3://<bucket>/<prefix>/ as the object ARN pattern under that prefix.
  done_objects     = "arn:aws:s3:::${trimprefix(var.done_prefix, "s3://")}*"
  artifact_objects = var.artifact_prefix == null ? [] : ["arn:aws:s3:::${trimprefix(var.artifact_prefix, "s3://")}*"]
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
    Statement = concat([
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
      # The done marker, first write only, under the server's own done prefix.
      {
        Sid      = "WriteOwnDoneMarkers"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = local.done_objects
      },
      ], length(local.artifact_objects) == 0 ? [] : [
      # The briefs the fire pass writes, and the diff, event log and result
      # the daemon uploads, all under the artifact prefix.
      {
        Sid      = "ReadBriefsWriteArtifacts"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = local.artifact_objects
      },
    ])
  })
}

resource "aws_iam_instance_profile" "server" {
  name = local.name
  role = aws_iam_role.server.name

  tags = var.cloud_tags
}

# IAM propagates a new instance profile and role policy in seconds, not at
# once. An instance launched straight after them misses its credentials at
# boot, and its SSM agent then backs off for about half an hour (CON-131 phase
# 2 acceptance). The instance waits here; the user data covers what is left.
resource "time_sleep" "instance_profile" {
  create_duration = "30s"

  depends_on = [aws_iam_instance_profile.server, aws_iam_role_policy.server]
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

  # Every server: wait for the instance-profile credentials, then restart the
  # SSM agent so it registers now; then set the OS hostname and install and
  # start the runner daemon from the presigned link. With Tailscale, the boot
  # join follows: the parameter path and names only, never a secret.
  user_data = join("", [
    file("${path.module}/ssm_agent_register.sh"),
    templatefile("${path.module}/agent_runner_boot.sh", {
      hostname       = var.hostname
      daemon_pkg_url = var.daemon_pkg_url
      queue_url      = aws_sqs_queue.server.url
      region         = data.aws_region.current.name
      prune_age_days = var.prune_age_days
      max_concurrent = var.max_concurrent
      claude_version = var.claude_version
      pi_package     = var.pi_package
      pi_version     = var.pi_version
    }),
    var.tailscale_join_parameter_path == null ? "" : templatefile("${path.module}/tailscale_join.sh", {
      region              = data.aws_region.current.name
      join_parameter_path = var.tailscale_join_parameter_path
      tailscale_tag       = var.tailscale_tag
      hostname            = var.hostname
    }),
  ])

  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.server.id]
  iam_instance_profile   = aws_iam_instance_profile.server.name

  depends_on = [time_sleep.instance_profile]

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
    # Every agent_server run asks for a new daemon link, so user_data differs
    # on every rerun, and the provider applies a user_data change by stopping
    # and starting the instance, which kills a running daemon. cloud-init runs
    # user data at the first boot only anyway: a later change (the link, a
    # Tailscale toggle) takes a delete and re-add of the server.
    ignore_changes = [user_data]

    precondition {
      condition     = var.public_subnet || length(local.nat_egress_routes) > 0
      error_message = "Subnet ${var.subnet_id} has no NAT egress: its route table ${data.aws_route_table.server.route_table_id} has no 0.0.0.0/0 default route to a NAT gateway, NAT instance or other egress target (an internet gateway route does not count for a private subnet). Config0 creates no NAT gateway. Add NAT egress to the VPC's routing, or choose a public subnet with the public-subnet option."
    }
  }
}

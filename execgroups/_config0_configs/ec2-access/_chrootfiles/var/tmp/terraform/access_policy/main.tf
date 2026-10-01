# One EC2 grant's inline permissions policy, per level.
#
# Provider-free on purpose: tests/authoring-guards/test_access_inline_policy.py
# evaluates it with `tofu console` and no AWS access. Levels follow the CON-11
# contract (ops work-log 2026-09-24/con-11-access-requests/contract.md,
# section 2b): ec2 has session, port_forward and ssh; ec2_windows has rdp.
#
# Every statement names the grant's one instance wherever the action takes a
# resource ARN. `*` appears only on actions whose Service Authorization
# Reference entry lists no resource type:
#   ssm:  https://docs.aws.amazon.com/service-authorization/latest/reference/list_ssm.html
#         (DescribeSessions, DescribeInstanceProperties, GetCommandInvocation,
#         GetInventorySchema)
#   ec2:  https://docs.aws.amazon.com/service-authorization/latest/reference/list_ec2.html
#         (DescribeInstances; "the ec2:Describe* API actions do not support
#         resource-level permissions", EC2 Instance Connect IAM page below)
#   ssmmessages: https://docs.aws.amazon.com/service-authorization/latest/reference/list_ssmmessages.html
#         ("does not support specifying a resource ARN"; OpenDataChannel on `*`
#         as in https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-default-session-document.html)
#   ssm-guiconnect: https://docs.aws.amazon.com/service-authorization/latest/reference/list_ssm-guiconnect.html

variable "level" {
  description = "The grant's EC2 access level: session, port_forward, ssh (ec2) or rdp (ec2_windows)"
  type        = string
}

variable "instance_id" {
  description = "The target EC2 instance id"
  type        = string
}

variable "aws_account_id" {
  description = "Account the instance lives in"
  type        = string
}

variable "aws_default_region" {
  description = "Region the instance lives in"
  type        = string
}

locals {
  instance_arn = "arn:aws:ec2:${var.aws_default_region}:${var.aws_account_id}:instance/${var.instance_id}"

  # An AWS-owned SSM document ARN carries no account; with an account id
  # Fleet Manager returns AccessDeniedException (Fleet Manager Remote Desktop
  # page, "Policy for connecting to EC2 instances with specific tags").
  aws_document = "arn:aws:ssm:${var.aws_default_region}::document"

  # The account's sessions; the session-id tag condition narrows them to the
  # caller's own (a session ARN is arn:aws:ssm:<region>:<account>:session/<id>,
  # https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-restrict-access.html).
  sessions_arn = "arn:aws:ssm:${var.aws_default_region}:${var.aws_account_id}:session/*"

  # Session Manager end-user statements shared by session and port_forward.
  # Source: "Sample IAM policies for Session Manager", Session Manager and
  # Fleet Manager tab,
  # https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-restrict-access-quickstart.html
  session_manager_common = [
    {
      # ssm:GetConnectionStatus takes the instance resource (list_ssm.html), so
      # it is scoped to the instance instead of the sample's `*`.
      Sid      = "ConnectionStatus"
      Effect   = "Allow"
      Action   = ["ssm:GetConnectionStatus"]
      Resource = [local.instance_arn]
    },
    {
      # End or resume only the caller's own sessions: the assumed-role form of
      # "Example 4, Method 2: Grant TerminateSession privileges using tags
      # supplied by AWS",
      # https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-restrict-access-examples.html
      Sid      = "OwnSessions"
      Effect   = "Allow"
      Action   = ["ssm:TerminateSession", "ssm:ResumeSession"]
      Resource = [local.sessions_arn]
      Condition = {
        StringLike = { "ssm:resourceTag/aws:ssmmessages:session-id" = ["$${aws:userid}*"] }
      }
    },
    {
      # No resource-level support; see the header.
      Sid    = "NoResourceArn"
      Effect = "Allow"
      Action = [
        "ssmmessages:OpenDataChannel",
        "ssm:DescribeSessions",
        "ssm:DescribeInstanceProperties",
        "ec2:DescribeInstances",
      ]
      Resource = "*"
    },
  ]

  # ssm:SessionDocumentAccessCheck = true makes Session Manager check the
  # document named in the request, or the default SSM-SessionManagerRunShell
  # when none is named, against this policy's document ARNs; without it the
  # default shell document is allowed implicitly. It must sit on every
  # statement that allows ssm:StartSession. Condition key:
  # https://docs.aws.amazon.com/service-authorization/latest/reference/list_ssm.html
  # (ssm:SessionDocumentAccessCheck on StartSession).
  session_document_check = {
    BoolIfExists = { "ssm:SessionDocumentAccessCheck" = "true" }
  }

  statements = {
    # A shell on the instance.
    session = concat([
      {
        Sid    = "StartSession"
        Effect = "Allow"
        Action = ["ssm:StartSession"]
        Resource = [
          local.instance_arn,
          "arn:aws:ssm:${var.aws_default_region}:${var.aws_account_id}:document/SSM-SessionManagerRunShell",
          "${local.aws_document}/AWS-StartInteractiveCommand",
        ]
        Condition = local.session_document_check
      },
    ], local.session_manager_common)

    # Port forwarding only, to the instance or through it to a remote host:
    # the bastion. No shell document is named, and the document check refuses
    # the default one. Documents: "Starting a session (port forwarding)" and
    # "(port forwarding to remote host)",
    # https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html
    port_forward = concat([
      {
        Sid    = "StartSession"
        Effect = "Allow"
        Action = ["ssm:StartSession"]
        Resource = [
          local.instance_arn,
          "${local.aws_document}/AWS-StartPortForwardingSession",
          "${local.aws_document}/AWS-StartPortForwardingSessionToRemoteHost",
        ]
        Condition = local.session_document_check
      },
    ], local.session_manager_common)

    # EC2 Instance Connect: push a public key to the instance, any OS user.
    # Source: "Grant IAM permissions for EC2 Instance Connect", "Allow users to
    # connect to specific instances",
    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-configure-IAM-role.html
    ssh = [
      {
        Sid      = "SendSSHPublicKey"
        Effect   = "Allow"
        Action   = ["ec2-instance-connect:SendSSHPublicKey"]
        Resource = [local.instance_arn]
      },
      {
        # "the ec2:Describe* API actions do not support resource-level
        # permissions. Therefore, the * wildcard is necessary" (same page).
        Sid      = "NoResourceArn"
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances"]
        Resource = "*"
      },
    ]

    # Fleet Manager Remote Desktop. Source: "Standard policy for connecting to
    # EC2 instances", narrowed to the one instance,
    # https://docs.aws.amazon.com/systems-manager/latest/userguide/fleet-manager-remote-desktop-connections.html
    rdp = [
      {
        Sid      = "StartSession"
        Effect   = "Allow"
        Action   = ["ssm:StartSession"]
        Resource = [local.instance_arn, "${local.aws_document}/AWS-StartPortForwardingSession"]
        Condition = {
          "ForAnyValue:StringEquals" = { "aws:CalledVia" = "ssm-guiconnect.amazonaws.com" }
        }
      },
      {
        # ec2:GetPasswordData takes the instance resource (list_ec2.html), so it
        # is scoped to the instance instead of the sample's `*`.
        Sid      = "PasswordData"
        Effect   = "Allow"
        Action   = ["ec2:GetPasswordData"]
        Resource = [local.instance_arn]
      },
      {
        Sid      = "OwnSessions"
        Effect   = "Allow"
        Action   = ["ssm:TerminateSession"]
        Resource = [local.sessions_arn]
        Condition = {
          StringLike = { "ssm:resourceTag/aws:ssmmessages:session-id" = ["$${aws:userid}"] }
        }
      },
      {
        # No resource-level support; see the header.
        Sid      = "DataChannel"
        Effect   = "Allow"
        Action   = ["ssmmessages:OpenDataChannel"]
        Resource = "*"
        Condition = {
          "ForAnyValue:StringEquals" = { "aws:CalledVia" = "ssm-guiconnect.amazonaws.com" }
        }
      },
      {
        # No resource-level support; see the header.
        Sid    = "NoResourceArn"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ssm:DescribeInstanceProperties",
          "ssm:GetCommandInvocation",
          "ssm:GetInventorySchema",
          "ssm-guiconnect:CancelConnection",
          "ssm-guiconnect:GetConnection",
          "ssm-guiconnect:StartConnection",
          "ssm-guiconnect:ListConnections",
        ]
        Resource = "*"
      },
    ]
  }

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = local.statements[var.level]
  })
}

output "policy" {
  description = "The inline permissions policy JSON for the grant's level"
  value       = local.policy
}

data "aws_caller_identity" "current" {}

###############################################################
# Variables
###############################################################

variable "aws_default_region" {
  default = "eu-west-1"
}

variable "step_function_name" {
  default = "apigateway-codebuild-ci"
}

variable "load_webhook" {
  default = "load_webhook"
}

variable "load_codebuild" {
  default = "load_codebuild"
}

variable "check_codebuild" {
  default = "check_codebuild"
}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}

###############################################################
# State Function
###############################################################

resource "aws_sfn_state_machine" "sfn_state_machine" {
  name     = var.step_function_name
  role_arn = aws_iam_role.step_function_role.arn

  definition = <<EOF
  {
    "Comment": "the state machine loads webhook from code repo, executes codebuild, and check results",
    "StartAt": "LoadWebhook",

    "States": {
      "LoadWebhook": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:${var.aws_default_region}:${data.aws_caller_identity.current.account_id}:function:${var.load_webhook}",
        "Next": "LoadCodebuild"
      },
      "LoadCodebuild": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:${var.aws_default_region}:${data.aws_caller_identity.current.account_id}:function:${var.load_codebuild}",
        "Next": "IsTotalCheckCodeBuildReached"
      },
      "IsTotalCheckCodeBuildReached": {
        "Type": "Choice",
        "Choices": [
          {
            "Variable": "$.num_of_runs",
            "NumericGreaterThan": 0,
            "Next": "CheckCodeBuildFirstRun"
          }
        ],
        "Default": "Done"
      },
      "CheckCodeBuildFirstRun": {
        "Type": "Choice",
        "Choices": [
          {
            "Variable": "$.is_first_run",
            "BooleanEquals": true,
            "Next": "CheckCodeBuildStatus"
          }
        ],
        "Default": "WaitState"
      },
      "WaitState": {
        "Type": "Wait",
        "SecondsPath": "$.wait_int",
        "Next": "CheckCodeBuildStatus"
      },
      "CheckCodeBuildStatus": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:${var.aws_default_region}:${data.aws_caller_identity.current.account_id}:function:${var.check_codebuild}",
        "Next": "CheckCodeBuildDone"
      },
      "CheckCodeBuildDone": {
        "Type": "Choice",
        "Choices": [
          {
            "Variable": "$.is_done",
            "BooleanEquals": true,
            "Next": "Done"
          }
        ],
        "Default": "IsTotalCheckCodeBuildReached"
      },
      "Done": {
        "Type": "Pass",
        "End": true
      }
    }
  }
  EOF
}

resource "aws_iam_role" "step_function_role" {
  name               = "${var.step_function_name}-role"
  assume_role_policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "sts:AssumeRole",
        "Principal": {
          "Service": "states.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": "StepFunctionAssumeRole"
      }
    ]
  }
  EOF
}

resource "aws_iam_role_policy" "step_function_policy" {
  name    = "${var.step_function_name}-policy"
  role    = aws_iam_role.step_function_role.id

  policy  = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "lambda:InvokeFunction"
        ],
        "Effect": "Allow",
        "Resource": [ "arn:aws:lambda:${var.aws_default_region}:${data.aws_caller_identity.current.account_id}:function:${var.load_webhook}",
                      "arn:aws:lambda:${var.aws_default_region}:${data.aws_caller_identity.current.account_id}:function:${var.load_codebuild}",
                      "arn:aws:lambda:${var.aws_default_region}:${data.aws_caller_identity.current.account_id}:function:${var.check_codebuild}" ]
      }
    ]
  }
  EOF
}


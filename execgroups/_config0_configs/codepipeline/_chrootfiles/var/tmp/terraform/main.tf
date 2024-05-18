provider "github" {}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type = "Service"

      identifiers = [
        "codebuild.amazonaws.com",
        "codepipeline.amazonaws.com",
      ]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "default" {
  name               = "${var.codepipeline_name}-role"
  assume_role_policy = "${data.aws_iam_policy_document.assume_role.json}"
}

data "aws_iam_policy_document" "default" {

  # CodePipeline and CodeBuild use CloudWatch logs for managing their console output.
  # This statement gives them them appropriate access according to the docs.
  statement {
    sid    = "AllowLogging"
    effect = "Allow"

    resources = ["*"]

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
  }

  #statement {
  #  sid    = "AllowAccessToTheKMSKey"
  #  effect = "Allow"

  #  resources = [
  #    "${aws_kms_key.default.arn}",
  #  ]

  #  actions = [
  #    "kms:DescribeKey",
  #    "kms:ListKeyPolicies",
  #    "kms:GetKeyPolicy",
  #    "kms:GetKeyRotationStatus",
  #    "kms:Encrypt",
  #    "kms:Decrypt",
  #    "kms:GenerateDataKey*",
  #    "kms:ReEncrypt*",
  #  ]
  #}

  statement {
    sid = "AllowAccessToArtifactsInS3"

    resources = [
      "arn:aws:s3:::${var.s3_bucket}",
      "arn:aws:s3:::${var.s3_bucket}/*",
    ]

    actions = [
      "s3:*",
    ]
  }

  statement {
    sid    = "AllowCodePipelineToManageResourcesItCreates"
    effect = "Allow"

    resources = [
      "arn:aws:s3:::codepipeline*",
      "arn:aws:s3:::elasticbeanstalk*",
    ]

    actions = [
      "s3:PutObject",
    ]
  }

  statement {
    sid    = "AllowCodePipelinToRunCodeDeploy"
    effect = "Allow"

    resources = [
      "*",
    ]

    actions = [
      "codedeploy:CreateDeployment",
      "codedeploy:GetApplicationRevision",
      "codedeploy:GetDeployment",
      "codedeploy:GetDeploymentConfig",
      "codedeploy:RegisterApplicationRevision",
    ]
  }

  statement {
    sid    = "AllowCodePipelineToSeeResources"
    effect = "Allow"

    resources = [
      "*",
    ]

    actions = [
      "elasticbeanstalk:CreateApplicationVersion",
      "elasticbeanstalk:DescribeApplicationVersions",
      "elasticbeanstalk:DescribeEnvironments",
      "elasticbeanstalk:DescribeEvents",
      "elasticbeanstalk:UpdateEnvironment",
      "autoscaling:DescribeAutoScalingGroups",
      "autoscaling:DescribeLaunchConfigurations",
      "autoscaling:DescribeScalingActivities",
      "autoscaling:ResumeProcesses",
      "autoscaling:SuspendProcesses",
      "cloudformation:GetTemplate",
      "cloudformation:DescribeStackResource",
      "cloudformation:DescribeStackResources",
      "cloudformation:DescribeStackEvents",
      "cloudformation:DescribeStacks",
      "cloudformation:UpdateStack",
      "ec2:DescribeInstances",
      "ec2:DescribeImages",
      "ec2:DescribeAddresses",
      "ec2:DescribeSubnets",
      "ec2:DescribeVpcs",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeKeyPairs",
      "elasticloadbalancing:DescribeLoadBalancers",
      "rds:DescribeDBInstances",
      "rds:DescribeOrderableDBInstanceOptions",
      "sns:ListSubscriptionsByTopic",
    ]
  }

  statement {
    sid    = "AllowCodePipelineToInvokeLambdaFunctions"
    effect = "Allow"

    resources = [
      "*",
    ]

    actions = [
      "lambda:invokefunction",
      "lambda:listfunctions",
    ]
  }

  statement {
    sid    = "AllowCodePipelineToManageBeanstalkS3Artifacts"
    effect = "Allow"

    resources = [
      "arn:aws:s3:::elasticbeanstalk*",
    ]

    actions = [
      "s3:ListBucket",
      "s3:GetBucketPolicy",
      "s3:GetObjectAcl",
      "s3:PutObjectAcl",
      "s3:DeleteObject",
    ]
  }

  statement {
    sid    = "AllowCodePipelineToManageCodeBuildJobs"
    effect = "Allow"

    resources = [
      "*",
    ]

    actions = [
      "codebuild:StartBuild",
      "codebuild:StopBuild",
      "codebuild:BatchGetBuilds",
      "codebuild:BatchGetProjects",
      "codebuild:ListBuilds",
      "codebuild:ListBuildsForProject",
      "codebuild:ListProjects",
    ]
  }
}

resource "aws_iam_role_policy" "default" {
  name   = "${var.codepipeline_name}-policy"
  role   = "${aws_iam_role.default.id}"
  policy = "${data.aws_iam_policy_document.default.json}"
}

#resource "aws_kms_key" "default" {
#  description = "kms key ${var.codepipeline_name}"
#}
#
#resource "aws_kms_alias" "default" {
#  name          = "alias/${var.codepipeline_name}"
#  target_key_id = "${aws_kms_key.default.key_id}"
#}

resource "aws_codepipeline" "default" {
  name     = var.codepipeline_name
  role_arn = "${aws_iam_role.default.arn}"

  artifact_store {
    location = var.s3_bucket
    type     = "S3"

    #encryption_key {
    #  id   = "${aws_kms_key.default.arn}"
    #  type = "KMS"
    #}

  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "ThirdParty"
      provider         = var.code_provider
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        Owner  = var.git_owner
        Repo   = var.git_repo
        Branch = var.git_branch
      }
    }
  }

  stage {
    name = "Build"

    action {
      name            = "Build"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      input_artifacts = ["source_output"]
      version         = "1"

      configuration = {
        ProjectName = var.codebuild_name
      }
    }
  }

}

#############################################################################
# Replace bottom with stack
#############################################################################

resource "aws_codepipeline_webhook" "default" {
  name            = "${var.codepipeline_name}-${var.code_provider}-webhook" 
  authentication  = "GITHUB_HMAC" 
  target_action   = "Source"
  target_pipeline = "${aws_codepipeline.default.name}"

  authentication_configuration {
    secret_token = var.webhook_secret
  }

  filter {
    json_path    = "$.ref"
    match_equals = "refs/heads/{Branch}"
  }
}

resource "github_repository_webhook" "default" {
  repository     = var.git_repo

  configuration {
    url          = "${aws_codepipeline_webhook.default.url}"
    content_type = "form"
    insecure_ssl = true
    secret       = "var.webhook_secret}"
  }

  events = ["push"]
}


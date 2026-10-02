resource "aws_ecs_cluster" "default" {
  name = var.ecs_cluster

  tags = merge(
    var.cloud_tags,
    {
      Name    = var.ecs_cluster
      Product = "ecs"
    },
  )
}

resource "aws_cloudwatch_log_group" "default" {
  name              = "/ecs/${var.ecs_cluster}/${var.ecs_service}"
  retention_in_days = var.log_retention_in_days

  tags = merge(
    var.cloud_tags,
    {
      Name    = var.ecs_service
      Product = "ecs"
    },
  )
}

data "aws_iam_policy_document" "ecs_tasks_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# The execution role: the ECS agent pulls the image and writes the logs.
resource "aws_iam_role" "execution" {
  name               = "${var.ecs_cluster}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json

  tags = merge(
    var.cloud_tags,
    {
      Product = "ecs"
    },
  )
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# The task role: ECS Exec runs the SSM agent in the task, which opens the
# session channels.
# https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html
resource "aws_iam_role" "task" {
  name               = "${var.ecs_cluster}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json

  tags = merge(
    var.cloud_tags,
    {
      Product = "ecs"
    },
  )
}

data "aws_iam_policy_document" "ecs_exec" {
  statement {
    actions = [
      "ssmmessages:CreateControlChannel",
      "ssmmessages:CreateDataChannel",
      "ssmmessages:OpenControlChannel",
      "ssmmessages:OpenDataChannel",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "ecs_exec" {
  name   = "ecs-exec"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.ecs_exec.json
}

resource "aws_ecs_task_definition" "default" {
  family                   = var.ecs_service
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = var.ecs_service
      image     = var.image
      essential = true
      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.default.name
          awslogs-region        = var.aws_default_region
          awslogs-stream-prefix = var.ecs_service
        }
      }
    }
  ])

  tags = merge(
    var.cloud_tags,
    {
      Name    = var.ecs_service
      Product = "ecs"
    },
  )
}

resource "aws_ecs_service" "default" {
  name            = var.ecs_service
  cluster         = aws_ecs_cluster.default.id
  task_definition = aws_ecs_task_definition.default.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  # ECS Exec, what an ecs access grant's exec level uses
  enable_execute_command = true

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }

  # the task role's ssmmessages permissions must exist before a task starts
  depends_on = [aws_iam_role_policy.ecs_exec]

  tags = merge(
    var.cloud_tags,
    {
      Name    = var.ecs_service
      Product = "ecs"
    },
  )
}

###########################################################################
# variables
###########################################################################
variable "aws_region" {
  default = "us-east-1"
}

variable "capacity_providers" {
  default = ["FARGATE_SPOT", "FARGATE"]
}

variable "default_capacity_provider" {
  default = "FARGATE_SPOT"
}

variable "ecs_cluster" {}

variable "cloud_tags" {
  description = "additional tags as a map"
  type        = map(string)
  default     = {}
}

###########################################################################
# fargate cluster
###########################################################################

resource "aws_ecs_cluster" "default" {
   name  = var.ecs_cluster
   capacity_providers = var.capacity_providers

   default_capacity_provider_strategy {
     capacity_provider = var.default_capacity_provider
   }

   #setting {
   # name  = "containerInsights"
   # value = "enabled"
   #}
}


# Account identity for the server record's ids and the key-set parameter ARNs.
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# The ec2_server execgroup's AMI read.
data "aws_ami" "default" {
  most_recent = true
  owners      = [var.ami_owner]

  filter {
    name   = "name"
    values = [var.ami_filter]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# NAT egress detection. These reads depend on tfvars only, so they resolve at
# plan, and the instance's precondition fails the plan before anything exists.
data "aws_subnet" "server" {
  id = var.subnet_id
}

# The subnet's own route table, if it has one; else the VPC's main table.
data "aws_route_tables" "subnet" {
  vpc_id = data.aws_subnet.server.vpc_id

  filter {
    name   = "association.subnet-id"
    values = [var.subnet_id]
  }
}

data "aws_route_tables" "main" {
  vpc_id = data.aws_subnet.server.vpc_id

  filter {
    name   = "association.main"
    values = ["true"]
  }
}

data "aws_route_table" "server" {
  route_table_id = length(data.aws_route_tables.subnet.ids) > 0 ? data.aws_route_tables.subnet.ids[0] : one(data.aws_route_tables.main.ids)
}

locals {
  # Customer NAT egress: a 0.0.0.0/0 route to any target but an internet
  # gateway, so a NAT gateway, a NAT instance (instance or network interface),
  # a transit gateway or a peering connection. A route to an internet gateway
  # makes the subnet public, which is the public-subnet option. Config0 creates
  # no NAT gateway and no endpoint-only substitute.
  nat_egress_routes = [
    for route in data.aws_route_table.server.routes : route
    if route.cidr_block == "0.0.0.0/0" && !can(regex("^igw-", route.gateway_id))
  ]
}

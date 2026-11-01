variable "hostname" {
  description = "The server's hostname; also names its role, instance profile, security group and queue"
  type        = string
}

variable "aws_default_region" {
  description = "AWS region where resources will be created"
  type        = string
}

variable "subnet_id" {
  description = "The subnet to launch the server in; a private subnet needs a 0.0.0.0/0 route to a NAT gateway"
  type        = string
}

variable "public_subnet" {
  description = "The public-subnet option: the server gets a public address and the NAT egress check is skipped"
  type        = bool
  default     = false
}

variable "key_parameter_paths" {
  description = "Comma-delimited SSM parameter paths of the named key sets the instance may read, never a prefix"
  type        = string
}

variable "done_prefix" {
  description = "The server's own done-marker prefix in the hub tmp bucket, s3://<bucket>/executions/agent/<hostname>/; the instance role may put objects under it only"
  type        = string
}

variable "artifact_prefix" {
  description = "The customer's bucket prefix, s3://<bucket>/<prefix>/, the server reads its briefs from and writes artifacts under (null: no artifact grant, the server takes no order)"
  type        = string
  default     = null
}

variable "tailscale_join_parameter_path" {
  description = "The tailscale_join set's SSM parameter path the server reads at boot to join the tailnet (null: no Tailscale, no join in the user data)"
  type        = string
  default     = null
}

variable "tailscale_tag" {
  description = "The tag the server joins the tailnet with, e.g. tag:config0 (Tailscale on only)"
  type        = string
  default     = null
}

variable "ssh_key_name" {
  description = "The key pair for the port 22 option (null: no key pair)"
  type        = string
  default     = null
}

variable "ssh_cidr" {
  description = "The CIDR allowed on port 22 for the port 22 option (null: no inbound port)"
  type        = string
  default     = null
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "disktype" {
  description = "EBS volume type for the root block device"
  type        = string
  default     = "gp2"
}

variable "disksize" {
  description = "Size of the root EBS volume in GB"
  type        = number
  default     = 20
}

variable "ami_filter" {
  description = "Filter pattern to locate specific AMI"
  type        = string
  default     = "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"
}

variable "ami_owner" {
  description = "AWS account ID of the AMI owner (Canonical for Ubuntu)"
  type        = string
  default     = "099720109477" # Canonical
}

variable "cloud_tags" {
  description = "Additional tags as a map to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "daemon_pkg_url" {
  description = "The presigned link to the runner daemon zip saas-api answers the agent_server run; the user data fetches it once, at first boot"
  type        = string
}

variable "prune_age_days" {
  description = "The runner daemon's worktree pruning age in days (CONFIG0_AGENT_PRUNE_AGE_DAYS)"
  type        = number
}

variable "max_concurrent" {
  description = "The orders the runner daemon runs at once (null: one per two vCPUs)"
  type        = number
  default     = null
}

variable "claude_version" {
  description = "The Claude Code release npm installs (@anthropic-ai/claude-code); the daemon needs 2.1.277 or later"
  type        = string
  default     = "2.1.316"
}

variable "pi_package" {
  description = "The npm package of the pi coding agent CLI"
  type        = string
  default     = "@earendil-works/pi-coding-agent"
}

variable "pi_version" {
  description = "The pi release npm installs; the daemon's event contract is pi 0.99.x"
  type        = string
  default     = "0.99.2"
}

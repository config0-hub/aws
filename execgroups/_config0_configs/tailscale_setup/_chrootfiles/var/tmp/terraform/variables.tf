variable "tailscale_tag" {
  description = "The tag the tailnet policy must own and grant, e.g. tag:config0"
  type        = string
}

variable "ssh_login" {
  description = "The OS login the policy's ssh accept rule must name, e.g. ubuntu"
  type        = string
}

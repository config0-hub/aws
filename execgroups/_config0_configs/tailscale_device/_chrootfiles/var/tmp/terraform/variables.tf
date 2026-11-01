variable "hostname" {
  description = "The agent server's hostname, the name it joined the tailnet with"
  type        = string
}

variable "tailscale_tag" {
  description = "The tag the server joined with, e.g. tag:config0; the device must carry it"
  type        = string
}

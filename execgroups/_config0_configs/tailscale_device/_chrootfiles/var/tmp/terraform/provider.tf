terraform {
  required_version = ">= 1.5"

  required_providers {
    tailscale = {
      source  = "tailscale/tailscale"
      version = "0.29.2"
    }
  }
}

# No credential lives in this module. The stack passes the tailscale_admin
# OAuth client as ssm_obj; the engine's reader sources that parameter as
# `export TAILSCALE_OAUTH_CLIENT_ID=...` and `export
# TAILSCALE_OAUTH_CLIENT_SECRET=...` before every tofu command, the two
# environment names this provider reads. delete_device.py reads the same two
# on destroy. The tailnet is the one that owns the client.
provider "tailscale" {}

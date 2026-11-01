# Every output lands on the device row (tf_configure._insert_outputs).
# agent_server's notify_success copies these three onto the server row.

output "tailscale_node_id" {
  value = terraform_data.device.output.node_id
}

output "tailscale_hostname" {
  description = "The device's full MagicDNS name, e.g. <hostname>.<tailnet>.ts.net"
  value       = data.tailscale_device.server.name
}

output "tailscale_tag" {
  value = var.tailscale_tag
}

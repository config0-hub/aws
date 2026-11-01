# An agent server's Tailscale device. On create it reads the device the server
# joined with at boot and writes nothing in the tailnet. On destroy it deletes
# that device through the API before the server's own destroy runs: this row
# is newer than the server row, and delete_resources_by_time removes the
# newest first. The provider has no resource that deletes a device.

# The join takes a minute or more after the instance starts. wait_for fits
# inside the order's 600 s timeout with init and plan.
data "tailscale_device" "server" {
  hostname = var.hostname
  wait_for = "420s"

  lifecycle {
    # Only the tagged device a server joined with is captured, so a destroy
    # never deletes a user's own device that happens to share the hostname.
    postcondition {
      condition     = contains(self.tags, var.tailscale_tag)
      error_message = "The tailnet device ${var.hostname} does not carry ${var.tailscale_tag}; it is not the device this server joined with."
    }
  }
}

resource "terraform_data" "device" {
  input = {
    node_id = data.tailscale_device.server.node_id
  }

  # DELETE /api/v2/device/{node_id} with the admin client. Any answer but 200
  # fails the destroy, and this resource stays in state with its row.
  provisioner "local-exec" {
    when        = destroy
    interpreter = ["python3"]
    command     = "${path.module}/delete_device.py"
    environment = {
      NODE_ID = self.input.node_id
    }
  }
}

# Every output lands on the resource row (tf_configure._insert_outputs), so
# only the checked tag is output: never the policy or the device list. The
# device read in main.tf is the admin client's scope proof and outputs nothing.
# No data source returns the tailnet's name, so none is output.

output "tailscale_tag" {
  value = terraform_data.policy_check.output.tailscale_tag
}

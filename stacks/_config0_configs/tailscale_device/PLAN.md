# tailscale_device: an agent server's Tailscale device (provisional names)

Reads the device an agent server joined the tailnet with, and deletes it before the server is
destroyed. Writes nothing in the tailnet on create. Design: ai-workflows round 10, §2c and M4.
Build plan: CON-131, phase 3.

## Placement

`agent_server` inserts it after its server order, in the same `server` job, only with
`tailscale_enabled`. Its row is therefore newer than the server row, and delete a server
(`delete_resources_by_time`, newest first) destroys it first.

## The stack (`_files/run.py`, Method Helper)

- Arguments: `hostname` (tfvar), `tailscale_tag` (tfvar, default `tag:config0`),
  `admin_set_name` (default `tailscale_admin`).
- `TAILSCALE_OAUTH_CLIENT_ID` and `TAILSCALE_OAUTH_CLIENT_SECRET` come from `stack.inputvars`,
  base64, decoded; a missing key fails naming the key and the set. The pair is passed as
  `ssm_obj`, the `tailscale_setup` pattern, so the engine's reader sources it before every
  tofu command, the destroy included, and the `secret` row is removed after the teardown.
- Write-back: `resource_type=tailscale_device`, the hostname as name, provider `tailscale`,
  promoted `tailscale_node_id`, `tailscale_hostname` (the full MagicDNS name) and
  `tailscale_tag`. `agent_server`'s `notify_success` copies them onto the server row.

## The execgroup (`execgroups/_config0_configs/tailscale_device/`)

- `tailscale/tailscale` pinned to `0.29.2`, an empty `provider "tailscale" {}` block.
- `data "tailscale_device"` by hostname with `wait_for = "420s"`, and a postcondition that
  the device carries the tag, so a user's own device of the same name is never captured.
- `terraform_data.device` holds `node_id`. Its destroy-time `local-exec` runs
  `delete_device.py` with `python3`: an OAuth token from the admin client, then
  `DELETE /api/v2/device/{node_id}`. Any answer but 200, a 404 included, fails the destroy, and
  the device, the server and their rows stay. The provider has no resource that deletes a
  device.
- A destroy re-reads the device first, so a device already removed by hand fails the destroy
  the same way.

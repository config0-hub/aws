# tailscale_setup: the Tailscale add-on's install stack (provisional names)

Checks the user's tailnet policy and the admin client's device scope. Writes nothing in
the tailnet. Design: ai-workflows round 10, §2c and M1 to M3. Build plan: CON-131, phase 1.

## Placement

saas-api places it as the Tailscale add-on's internal project, one run per install
(the add-on path `dispatch_addon_stack` already uses). Before dispatch, saas-api checks
that both input variable sets exist for the hub account. It writes the `tailscale_admin`
reference row on the add-on schedule, so the worker resolves that set into
`stack.inputvars`. The `tailscale_join` set is never referenced on the schedule.

## The stack (`_files/run.py`, Class Helper)

- Arguments: `admin_set_name` (default `tailscale_admin`), `join_set_name` (default
  `tailscale_join`, recorded only), `tailscale_tag` (tfvar, default `tag:config0`),
  `ssh_login` (tfvar, default `ubuntu`), `stateful_id`, and the add-on identity
  `workflow_id`, `attempt_id`, `owner_id`. The identity is required, because only saas-api
  places this stack.
- `install`: one Terraform order on the `tailscale_setup` execgroup through `tf_executor`.
  `TAILSCALE_OAUTH_CLIENT_ID` and `TAILSCALE_OAUTH_CLIENT_SECRET` come from
  `stack.inputvars`. The user enters each value base64, and the stack decodes it.
  A missing key fails, naming the key and the set. The pair is passed as `ssm_obj`
  (the `github_ssh_upload` pattern). `TFConstructor` writes it with `add_secret`, and the
  `secret` row holds the path only. The engine's reader sources it before every tofu
  command. Its keys are the provider's own environment names, so nothing is renamed.
- `notify_success`: reads the install's `tailscale_setup` row (the tag the checked plan
  output), then writes two rows inline: the `tailnet` row (the tag and both set names,
  never a value), then the `addon` record, `_id = md5("addon:tailscale")`.
- `notify_failure`, on every `on_failure` edge: `config0 gitops notify ... status=FAILED`,
  `key=tailscale`.
- No `on_delete` edges. A removal is `callback_delete` over the install schedule
  (addon-lifecycle-contract: no run walks `on_delete`). It tears down the Terraform row
  and the `secret` row, then unrecords the `tailnet` row. `keep_resources` keeps the
  `addon` record, which run_complete's sweep removes.

## The execgroup (`execgroups/_config0_configs/tailscale_setup/`)

- `tailscale/tailscale` pinned to `0.29.2`. An empty `provider "tailscale" {}` block, so
  no credential lives in Terraform variables or state.
- `data "tailscale_acl"` and `data "tailscale_devices"`. A `terraform_data` with four
  preconditions, each naming its missing entry: `tagOwners["tag:config0"]`, the
  member-to-tag grant, the tag-to-tag grant, and the `ssh` accept rule for the login.
- Outputs: `tailscale_tag` only. Every output lands on the resource row, so the device read
  outputs nothing.
  No data source returns the tailnet's name (M6), so none is output.
- No `tailscale_*` resource. The guard `tests/authoring-guards/test_tailscale_setup_read_only.py`
  fails if one appears.

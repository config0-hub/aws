# agent_server: one agent server and its own queue (provisional names)

Creates one server per hostname, reached over Session Manager by default. Design:
ai-workflows round 10, §2b, B and L1 to L3; Tailscale §2c and M4. Build plan: CON-131, phases
2 to 4. Every server runs the runner daemon, installed at first boot (R1-5).

## Placement

From the add-on card, saas-api places it as one internal add-on project per hostname, one
run per add a server. Before any write it refuses unless the AI workflows add-on is
installed and a key set exists. With port 22 it writes the SSH set's reference row on the
add-on schedule, so the worker resolves that set into `stack.inputvars`. An author's own
composition may also run it, without the add-on identity.

## The stack (`_files/run.py`, Class Helper)

- Arguments: `hostname`; `subnet_id`; `public_subnet` (off); `aws_default_region`; the
  instance size inputs as `aws_ec2_server` takes them (`instance_type`, `ami_filter`,
  `ami_owner`, `disktype`, `disksize`); `ssh_enabled` (off), with `ssh_cidr` and
  `ssh_set_name` only when on; `key_set_names` (default
  `CLAUDE_CODE_OAUTH_TOKEN,ANTHROPIC_API_KEY,OPENAI_API_KEY`); `artifact_prefix` (optional,
  the customer's `s3://<bucket>/<prefix>/` for briefs and artifacts); `prune_age_days` (default
  7, the daemon's worktree pruning age) and `max_concurrent` (optional; unset, one order per two
  vCPUs), both tfvars only; `lifetime` (`permanent` or
  `per_run`, default `permanent`); `tailscale_enabled` (off), with `tailscale_join_set_name`
  (default `tailscale_join`), `tailscale_admin_set_name` (default `tailscale_admin`) and
  `tailscale_tag` (default `tag:config0`); and the add-on identity `workflow_id`,
  `attempt_id`, `owner_id`, optional.
- `server`: with port 22 only, an `ec2_ssh_upload` substack order for the key pair
  `agent-server-<hostname>`; `ec2_ssh_upload` reads `public_key` from `stack.inputvars`.
  Then one Terraform order on the `agent_server` execgroup through `tf_executor`, with the
  presigned daemon link `stack.get_daemon_link()` read from saas-api as a tfvar. The key
  set names become the parameter paths `/config0/<CONFIG0_OWNER_ID>/inputvars/<name>`; a
  name with `*`, `?` or `/` fails loud, and so does the admin set's name among them. Write-back:
  `resource_type=server`, the hostname as name, promoted `account_id`, `region`,
  `instance_id`, `instance_profile`, `iam_role_arn` and `queue_url`, the flat label
  `labels_lifetime`, `addon_id` on the add-on path, and `tailscale: true` with Tailscale on.
  The grants FIRE checks ride as lists (G4): `artifact_prefixes` (the artifact prefix, when set,
  and the server's done prefix `s3://<TMP_BUCKET>/executions/agent/<hostname>/`) and
  `key_parameter_paths` (the named set paths).
- Tailscale on: before any order, the admin set's two keys must be in `stack.inputvars`. The
  join set's path joins the named reads, and `tailscale_join_parameter_path` and
  `tailscale_tag` become tfvars for the boot join. After the server order, one
  `tailscale_device` substack order (hostname, tag, admin set name) captures the device.
- `notify_success`: with Tailscale on, reads the `tailscale_device` row and the server row
  of this schedule and merges `tailscale_hostname`, `tailscale_tag` and `tailscale_node_id`
  onto the server row with `update_resource`, with `tailscale: true` again. Then, only when the add-on route set
  `attempt_id`, writes the server's
  `addon` record inline: `_id = md5("addon:ai_workflows:<hostname>")`, `addon=ai_workflows`,
  `hostname`, `attempt_id`, `workflow_id`.
- `notify_failure`, on every `on_failure` edge: `config0 gitops notify ... status=FAILED`,
  `key=ai_workflows:<hostname>`. An author's run carries no `workflow_id`, so it writes
  nothing.
- No `on_delete` edges. Delete a server is `callback_delete` over the server's add-on
  schedule: newest first, the `tailscale_device` row's destroy (the device deleted through the
  API), the server row's destroy (instance, queue, security group, profile, role), then the
  key pair row, then the admin client's `secret` row. `keep_resources` keeps the `addon` record for
  run_complete's sweep. A failed destroy keeps the rows and reports FAILED.

## The execgroup (`execgroups/_config0_configs/agent_server/`)

- `hashicorp/aws` `~> 5.0`, locked at 5.95.0, the `ec2_server` execgroup's provider.
- The instance role's inline policy: the four `ssmmessages` channel actions and
  `ssm:UpdateInstanceInformation`; `ssm:GetParameter` on the named key-set parameters, and the
  `tailscale_join` parameter with Tailscale on, only;
  `sqs:ReceiveMessage` and `sqs:DeleteMessage` on its own queue; `s3:PutObject` under its own
  done prefix only; `s3:GetObject` and `s3:PutObject` under the artifact prefix, when set. No
  managed policy, never
  `AmazonSSMManagedInstanceCore`.
- A security group with no inbound rule unless `ssh_cidr` is set, and egress to anywhere.
- NAT egress: the subnet's route table (its own, else the VPC's main table) must route
  `0.0.0.0/0` to a NAT gateway unless `public_subnet` is on. A precondition on the instance
  fails the plan, naming the subnet and the route table. Config0 creates no NAT gateway.
- The instance: the `ec2_server` execgroup's AMI read and root disk; no public address
  unless `public_subnet`; the key pair only with port 22.
- User data on every server, in order: `ssm_agent_register.sh` (wait for the instance-profile
  credentials, restart the SSM agent); `agent_runner_boot.sh` through `templatefile` (Node 22
  from NodeSource, `claude` and `pi` pinned by `claude_version`, `pi_package` and `pi_version`,
  the one fetch of the daemon link, `install.sh` with the queue URL, region, pruning age and
  `max_concurrent`); then, with Tailscale on, the join below. The instance ignores later
  `user_data` changes: a new link or setting takes a delete and re-add.
- The Tailscale join: `tailscale_join.sh` through `templatefile`, with the
  parameter path, the server's region, the tag and the hostname. At first boot it installs
  `curl` and `python3-boto3`, then Tailscale with its install script; reads the join set with
  the instance role, decodes the base64 JSON and then the value; runs `tailscale up` with the
  secret as the auth key, `ephemeral=false&preauthorized=true`, `--advertise-tags`,
  `--hostname` and `--ssh`; then unsets the variable. No port and no key pair are added.

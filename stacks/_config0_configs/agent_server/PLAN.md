# agent_server: one agent server and its own queue (provisional names)

Creates one server per hostname, reached over Session Manager by default. Design:
ai-workflows round 10, §2b, B and L1 to L3. Build plan: CON-131, phase 2. No runner daemon
and no boot assets yet (M4): the server's user data is empty, as `aws_ec2_server`'s default.

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
  `CLAUDE_CODE_OAUTH_TOKEN,ANTHROPIC_API_KEY,OPENAI_API_KEY`); `lifetime` (`permanent` or
  `per_run`, default `permanent`); and the add-on identity `workflow_id`, `attempt_id`,
  `owner_id`, optional.
- `server`: with port 22 only, an `ec2_ssh_upload` substack order for the key pair
  `agent-server-<hostname>`; `ec2_ssh_upload` reads `public_key` from `stack.inputvars`.
  Then one Terraform order on the `agent_server` execgroup through `tf_executor`. The key
  set names become the parameter paths `/config0/<CONFIG0_OWNER_ID>/inputvars/<name>`; a
  name with `*`, `?` or `/` fails loud. Write-back: `resource_type=server`, the hostname as
  name, promoted `account_id`, `region`, `instance_id`, `instance_profile`, `iam_role_arn`
  and `queue_url`, the flat label `labels_lifetime`, and `addon_id` on the add-on path.
- `notify_success`: only when the add-on route set `attempt_id`, writes the server's
  `addon` record inline: `_id = md5("addon:ai_workflows:<hostname>")`, `addon=ai_workflows`,
  `hostname`, `attempt_id`, `workflow_id`.
- `notify_failure`, on every `on_failure` edge: `config0 gitops notify ... status=FAILED`,
  `key=ai_workflows:<hostname>`. An author's run carries no `workflow_id`, so it writes
  nothing.
- No `on_delete` edges. Delete a server is `callback_delete` over the server's add-on
  schedule: newest first, the server row's destroy (instance, queue, security group,
  profile, role), then the key pair row. `keep_resources` keeps the `addon` record for
  run_complete's sweep. A failed destroy keeps the rows and reports FAILED.

## The execgroup (`execgroups/_config0_configs/agent_server/`)

- `hashicorp/aws` `~> 5.0`, locked at 5.95.0, the `ec2_server` execgroup's provider.
- The instance role's inline policy: the four `ssmmessages` channel actions and
  `ssm:UpdateInstanceInformation`; `ssm:GetParameter` on the named key-set parameters only;
  `sqs:ReceiveMessage` and `sqs:DeleteMessage` on its own queue. No managed policy, never
  `AmazonSSMManagedInstanceCore`.
- A security group with no inbound rule unless `ssh_cidr` is set, and egress to anywhere.
- NAT egress: the subnet's route table (its own, else the VPC's main table) must route
  `0.0.0.0/0` to a NAT gateway unless `public_subnet` is on. A precondition on the instance
  fails the plan, naming the subnet and the route table. Config0 creates no NAT gateway.
- The instance: the `ec2_server` execgroup's AMI read and root disk; no public address
  unless `public_subnet`; the key pair only with port 22.

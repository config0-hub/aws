# ai_workflows_install: the AI workflows add-on's install stack (provisional names)

Records the add-on. Creates nothing in AWS: no Terraform order, no server, no queue.
Design: ai-workflows round 10, §2b and L1 to L3. Build plan: CON-131, phase 2.

The design names this stack only "the AI workflows add-on's install stack";
`ai_workflows_install` is the build's provisional name.

## Placement

saas-api places it as the AI workflows add-on's internal project, one run per install
(the add-on path `dispatch_addon_stack` already uses). Before any write, saas-api refuses
with 409 unless an input variable set named `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY`
or `OPENAI_API_KEY` exists for the hub account. The stack reads no secret.

## The stack (`_files/run.py`, Class Helper)

- Arguments: the add-on identity `workflow_id`, `attempt_id`, `owner_id`, required,
  because only saas-api places this stack.
- `notify_success`, the one entry job: writes the `addon` record inline,
  `_id = md5("addon:ai_workflows")`, `addon=ai_workflows`, with `attempt_id` and
  `workflow_id`. It emits no order.
- `notify_failure`, on the `on_failure` edge: `config0 gitops notify ... status=FAILED`,
  `key=ai_workflows`.
- No `on_delete` edges. Uninstall is `callback_delete` over the install schedule
  (addon-lifecycle-contract: no run walks `on_delete`). The install wrote no other row, so
  `keep_resources` keeps the `addon` record for run_complete's sweep. saas-api refuses the
  uninstall while any add-on server row exists.

## Keys the readers map

| Record | `addon` | Other key field | owner_state key | `_id` |
|---|---|---|---|---|
| The add-on | `ai_workflows` | none | `ai_workflows` | `md5("addon:ai_workflows")` |
| A server (`agent_server`) | `ai_workflows` | `hostname` | `ai_workflows:<hostname>` | `md5("addon:ai_workflows:<hostname>")` |

The server key is the `ssm_ec2_exec:<region>` shape with the hostname in place of the region.

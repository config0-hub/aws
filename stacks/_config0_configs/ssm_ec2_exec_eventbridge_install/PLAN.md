# v2 authoring install — plan (CORRECTED: bucket is a separate stack, found by selector)

Installs the vetted standalone `ssm-ec2-exec-eventbridge` tool via the config0 platform,
using the config0-native cross-resource pattern (the vpc-rds-multistack precedent): the
S3 bucket is its OWN stack with its OWN state, recorded to the resources DB; the install
stack finds the bucket by a SELECTOR query. No shared terraform state, no bucket name
threaded through run.py memory.

## Composition — project-level config0.yaml (mirrors vpc-rds-multistack)
```
stacks:
  lambda_bucket:   # the existing aws_s3_bucket stack — creates + records the bucket (resource_type cloud_storage),
                   #   carries a label so it is selectable
  ssm_v2_install:  # the new stack below — dependencies: [lambda_bucket]; selects the bucket name;
                   #   builds the zips (CodeBuild) then creates the infra (terraform)
```
The `dependencies: [lambda_bucket]` edge makes the selector resolve in the same run (order gate
holds the install until the bucket record is written back — confirmed with config0-order-queue).

## The install stack = aws-lambda-python-codebuild shape (ONE build order + ONE terraform order)
No second TFConstructor, so no shared-state collision (that was my earlier mistake — the bucket
is now a separate stack, not a second terraform order here).

`stacks/_config0_configs/ssm_ec2_exec_eventbridge_install/_files/run.py`:
- Inputs: v1-install `aws_region` (tfvar) + aws-lambda-python-codebuild codebuild optionals
  (runtime=python3.12, compute_type, image_type, build_timeout, codebuild_role, cloud_tags_hash,
  stateful_id, execution_id, share_dir, script_name). Plus a **required `s3_bucket`** that the
  config0.yaml supplies as a `selector:::<name>::s3_bucket` expression (resolved to the bucket
  name before the run).
- Declare 2 execgroups (`lambda_build`, `tf_execgroup`) + 1 `config0_core::tf_executor` substack.
  init_variables/execgroups/substacks.
- `key_prefix = f"{stack.execution_id}/"` (execution-scoped so rebuilt zips get a fresh s3_key
  → the Lambda actually redeploys; Decision 2).
- ORDER 1 (CodeBuild): `lambda_build.insert(...)` with build_envs mirroring
  aws-lambda-python-codebuild run.py:169-214 but `S3_BUCKET=stack.s3_bucket` (the selected bucket),
  `KEY_PREFIX=key_prefix`, `PYTHON_VERSION 3.12`, `script_name=docker-to-lambda.sh` (the script
  loops all 3 lambdas — no per-lambda name).
- ORDER 2 (terraform): `TFConstructor(resource_name ssm_ec2_exec_eventbridge, type
  ssm_ec2_exec_eventbridge_install)`, `tf.include(values={aws_region, s3_bucket=stack.s3_bucket,
  s3_key_starter=f"{key_prefix}starter.zip", _callback, _fallback})`,
  `tf.output(keys=[state_machine_arn, bucket_name, instance_profile_name, dynamodb_table_name])`,
  `tf_executor.insert(display=True, **tf.get())`. NO automation_phase. NEVER set_parallel().
  NOTE (verified against terraform.py:333): `tf.include(values=...)` only records values on
  the resource surface; it does NOT feed terraform. So `s3_bucket` is declared `tags="tfvar"`
  and the three computed `s3_key_*` are set via `stack.set_variable(..., tags="tfvar")` (recorded
  in set_vars_manual so the TFConstructor reset preserves them) → TF_VAR_s3_bucket / TF_VAR_s3_key_*.
  `aws_region` already carries the tfvar tag.

## Execgroups (under src/authoring/aws/execgroups/_config0_configs/)  — 2 kept, 1 dropped
- KEEP `ssm_ec2_exec_eventbridge_lambda_build/` (already built + validated) — codebuild action +
  standalone `lambdas/` verbatim; `docker-to-lambda.sh` honors `KEY_PREFIX`.
- KEEP `ssm_ec2_exec_eventbridge_install/` (already built + validated) — resource_wrapper action +
  standalone `terraform/` verbatim except `lambda.tf` (references var.s3_bucket/var.s3_key_*, no
  aws_s3_object/local source) and `variables.tf` (+ the 4 vars).
- DROP `ssm_ec2_exec_eventbridge_bucket/` — the existing `src/authoring/aws_storage/.../aws_s3_bucket`
  stack is the bucket; no need for a bespoke one.

## config0.yaml scenario (config0_yamls_repos, new folder, mirror vpc-rds-multistack)
- `stacks.lambda_bucket` = `aws_s3_bucket` (its FQN), with a bucket name + a label
  (e.g. `purpose: ssm-ec2-exec-eventbridge`).
- `stacks.ssm_v2_install` = the new install stack FQN, `dependencies: [lambda_bucket]`, and
  `s3_bucket: selector:::bucket_vars::s3_bucket`.
- A top-level `selectors:` block: `bucket_vars` matching `resource_type: cloud_storage` + the label.

## Honest net-new bit (flagged)
No original finds a lambda-zip bucket by SELECTOR — the originals thread it as a plain `s3_bucket`
argument. The building blocks (aws_s3_bucket record at resource_type cloud_storage + the standard
selector machinery + the dependency gate) are all proven; the bucket-by-selector wiring for lambda
zips is the one net-new combination. This is the pattern the user explicitly wants ("query the
bucket like any other resource"). The live install proves it.

## Gates already confirmed
- Order-queue: sequential inserts + a `dependencies:` edge serialize (subtree-closed gate); same-run
  selector resolves after the producer writes back. No explicit deps needed between the install's own
  two orders; the cross-stack edge is the config0.yaml `dependencies:`.

#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# openci-tf config0-addon tofu stages: ecr and deploy (create and destroy).
#
# Runs in the engine's CodeBuild through the codebuild-srcfile script (the
# same framing as the image-copy stage and the ssm lambda_build order): the
# openci_tf_install stack seals this file's inputs into the build environment,
# the engine extracts the src zip and runs ./openci-tf-addon-tofu.py at its
# root. The engine image carries git, python3, and boto3; tofu is installed
# here at the pinned TOFU_VERSION because openci-tf needs >= 1.10 (S3 native
# lock file) and the engine image pins an older one. The tenant config0-worker
# Lambda has neither git nor tofu, which is why these two stages are not in
# openci-tf-addon-stage.
#
#   STAGE                 ecr | deploy
#   METHOD                create (default) | destroy
#   OPENCI_TF_REPO_URL    https://github.com/<owner>/openci-tf.git
#   OPENCI_TF_GIT_REF     the pinned 40-char commit sha
#   TOFU_VERSION          the OpenTofu release to install
#   OPENCI_TF_REGION, OPENCI_TF_PROJECT, STATE_BUCKET, ENGINE_NAME, TRIGGER_ID,
#   API_CALLER_ROLE_ARNS, TARGET_ACCOUNT_IDS: the installer inputs, exactly the
#   arguments `just install-config0-addon` passes to install/config0_addon.py.
#
# create ecr     install/config0_addon.py --stage ecr   (targeted module.ecr)
# create deploy  install/config0_addon.py --stage deploy, then the infra/deploy
#                outputs are recorded to SSM /openci-tf/install/<project>/
#                config0_outputs for the register and record stages
# destroy ecr    tofu destroy -target=module.ecr (after the image-copy stage
#                deleted its tag)
# destroy deploy tofu destroy of every non-ECR deploy module, then foundation;
#                the recorded outputs parameter is deleted
#
# A destroy prints the CONFIG0_DESTROY_PRE/POST_STATE_COUNT markers the CLI's
# execgroup destroy finalizer reads from the engine ExecutionResult: the
# counts are `tofu state list` before and after, scoped to the modules this
# stage owns, summed over the roots it destroys. A root whose owned modules
# are already gone (a re-fired order after a prior attempt's teardown) is
# skipped, not destroyed again: infra/deploy's data sources read the
# foundation buckets and KMS alias, so a second `tofu destroy` there fails at
# refresh once the foundation is gone (CodeBuild 698cb532, 17 s).
#
# Every tofu call here passes -no-color and the markers follow a newline
# flush: tofu's colored output ends with its ANSI reset AFTER the final
# newline, which put the PRE marker mid-line and the finalizer read "found 0".
# ---------------------------------------------------------------------------
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

STAGES = ("ecr", "deploy")
_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")


def env(name, default=None):
    value = os.environ.get(name, default)
    if not value:
        raise KeyError(f"{name} is required")
    return value


def install_tofu(version, bin_dir):
    """Put tofu:{version} on PATH (urllib + zipfile: the tfinstaller pattern)."""
    os.makedirs(bin_dir, exist_ok=True)
    url = (
        "https://github.com/opentofu/opentofu/releases/download/"
        f"v{version}/tofu_{version}_linux_amd64.zip"
    )
    zip_path = os.path.join(bin_dir, f"tofu_{version}.zip")
    with urllib.request.urlopen(url, timeout=120) as src, open(zip_path, "wb") as out:
        shutil.copyfileobj(src, out)
    dst = os.path.join(bin_dir, "tofu")
    with zipfile.ZipFile(zip_path) as archive, archive.open("tofu") as member, open(dst, "wb") as out:
        shutil.copyfileobj(member, out)
    os.chmod(dst, 0o755)
    os.remove(zip_path)
    os.environ["PATH"] = f"{bin_dir}:{os.environ['PATH']}"
    print(f"installed tofu {version} at {dst}", flush=True)


def checkout(repo_url, git_ref, dest):
    """Clone and pin to exactly git_ref; the resulting HEAD is verified."""
    if not _COMMIT_SHA.fullmatch(git_ref):
        raise ValueError(f"OPENCI_TF_GIT_REF must be a 40-char commit sha, got {git_ref!r}")
    subprocess.run(["git", "clone", "--quiet", repo_url, dest], check=True)
    subprocess.run(["git", "-C", dest, "checkout", "--quiet", git_ref], check=True)
    head = subprocess.run(
        ["git", "-C", dest, "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    if head != git_ref:
        raise ValueError(f"checked out {head} but the pinned ref is {git_ref}")
    return dest


def _installer_argv(stage):
    argv = [
        "--stage", stage,
        "--region", env("OPENCI_TF_REGION"),
        "--project-name", env("OPENCI_TF_PROJECT"),
        "--state-bucket", env("STATE_BUCKET"),
        "--engine-name", env("ENGINE_NAME"),
    ]
    trigger_id = os.environ.get("TRIGGER_ID")
    if stage == "deploy" and trigger_id:
        argv += ["--trigger-id", trigger_id]
        for arn in [a for a in os.environ.get("API_CALLER_ROLE_ARNS", "").split(",") if a]:
            argv += ["--api-caller-role-arn", arn]
    for account_id in [a for a in os.environ.get("TARGET_ACCOUNT_IDS", "").split(",") if a]:
        argv += ["--target-account-id", account_id]
    return argv


def _installer(source):
    """openci-tf's own installer module: prepare_root/deploy_tfvars keep the
    backend, tfvars, and init flags identical between apply and destroy."""
    sys.path.insert(0, os.path.join(source, "install"))
    import config0_addon  # noqa: PLC0415 - importable only after the checkout
    return config0_addon


def _outputs_param():
    return f"/openci-tf/install/{env('OPENCI_TF_PROJECT')}/config0_outputs"


def _arn_region(arn):
    """The region field of an AWS ARN, or None (global services leave it empty)."""
    if isinstance(arn, str) and arn.startswith("arn:"):
        parts = arn.split(":")
        if len(parts) > 3 and parts[3]:
            return parts[3]
    return None


def _ecr_repository_identity(resources):
    """(project, region) from the deploy state's ``aws_ecr_repository``, or None.

    The repository ``name`` IS the install project (infra/deploy/modules/ecr:
    ``name = var.project_name``) and its ``arn`` carries the region. Read from
    the resource, NOT a root output: a targeted ``apply -target=module.ecr``
    (the ecr stage) does not evaluate root outputs, so the fresh-install deploy
    state has ``module.ecr`` resources but no ``project_name`` output. The ecr
    repository is in the deploy state in every shape - the ecr stage creates it
    before the deploy stage, and the full deploy apply keeps it."""
    for resource in resources:
        if resource.get("type") != "aws_ecr_repository":
            continue
        for instance in resource.get("instances", []):
            attributes = instance.get("attributes") or {}
            name = attributes.get("name")
            recorded_region = _arn_region(attributes.get("arn"))
            if name and recorded_region:
                return name, recorded_region
    return None


def _existing_state_identity(state_bucket, state_key, region, *, s3=None):
    """(project, region) recorded in the tofu state at
    ``<state_key>/terraform.tfstate`` in ``state_bucket``, or None when the
    object is absent or holds no managed resources.

    The install's backend key is fixed (``generate_backend.sh``), so when this
    object exists ``tofu init`` reads it and ``tofu apply`` adopts the recorded
    resources instead of recreating them. None means a fresh install. A
    non-empty state with no ``aws_ecr_repository`` to identify fails loud - the
    guard must never apply blindly against an unidentifiable state."""
    from botocore.exceptions import ClientError

    if s3 is None:
        import boto3

        s3 = boto3.client("s3", region_name=region)
    key = f"{state_key}/terraform.tfstate"
    try:
        body = s3.get_object(Bucket=state_bucket, Key=key)["Body"].read()
    except ClientError as error:
        if error.response["Error"]["Code"] in ("NoSuchKey", "NoSuchBucket"):
            return None
        raise
    state = json.loads(body)
    if not state.get("resources"):
        return None
    identity = _ecr_repository_identity(state["resources"])
    if identity is None:
        raise ValueError(
            f"openci-tf install: existing state s3://{state_bucket}/{key} holds "
            "resources but no aws_ecr_repository to verify project/region against"
        )
    return identity


def verify_state_adoption(stage, *, s3=None):
    """Refuse to apply against a state that belongs to a different install.

    When ``deploy/terraform.tfstate`` already exists in the tenant state bucket
    (a re-install after a permanent Config0 deletion left the tenant bucket and
    its state intact), its recorded project/region MUST match this install; the
    fixed backend key then makes ``tofu apply`` adopt those resources. A fresh
    install (no state) proceeds unchanged. Both the ecr and deploy stages write
    the ``deploy`` root, whose ``project_name`` output is the install identity,
    so guarding that state covers both."""
    state_bucket = env("STATE_BUCKET")
    project = env("OPENCI_TF_PROJECT")
    region = env("OPENCI_TF_REGION")
    identity = _existing_state_identity(state_bucket, "deploy", region, s3=s3)
    if identity is None:
        print(
            f"{stage}: no existing openci-tf deploy state in {state_bucket}; "
            "fresh install",
            flush=True,
        )
        return
    recorded_project, recorded_region = identity
    if recorded_project != project or recorded_region != region:
        raise ValueError(
            "openci-tf install: refusing to apply against an existing state for a "
            f"different install - s3://{state_bucket}/deploy/terraform.tfstate "
            f"records project={recorded_project!r} region={recorded_region!r}, "
            f"this install is project={project!r} region={region!r}"
        )
    print(
        f"{stage}: adopting existing openci-tf state "
        f"(project={recorded_project}, region={recorded_region}) in {state_bucket}",
        flush=True,
    )


def create(stage, source):
    verify_state_adoption(stage)
    subprocess.run(
        [sys.executable, "install/config0_addon.py", *_installer_argv(stage)],
        cwd=source, check=True,
    )
    if stage != "deploy":
        return
    import boto3

    completed = subprocess.run(
        ["tofu", "-chdir=infra/deploy", "output", "-json", "-no-color"],
        cwd=source, check=True, capture_output=True, text=True,
    )
    outputs = {
        key: value["value"]
        for key, value in json.loads(completed.stdout).items()
        if not value.get("sensitive")
    }
    boto3.client("ssm", region_name=env("OPENCI_TF_REGION")).put_parameter(
        Name=_outputs_param(), Value=json.dumps(outputs), Type="String", Overwrite=True,
    )
    print(f"deploy outputs recorded to {_outputs_param()}", flush=True)


def state_addresses(source, root):
    """The managed resource addresses in one root's state (empty when none)."""
    completed = subprocess.run(
        ["tofu", f"-chdir={root}", "state", "list", "-no-color"],
        cwd=source, check=True, capture_output=True, text=True,
    )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def owned(addresses, targets):
    """The addresses under the targeted modules (all of them when targets is None)."""
    if targets is None:
        return list(addresses)
    return [
        address for address in addresses
        if any(address == t or address.startswith((f"{t}.", f"{t}[")) for t in targets)
    ]


def destroy_root(source, root, targets=None):
    """tofu destroy of the targeted modules (or the whole root); returns the
    (pre, post) counts of owned addresses in state. Nothing owned in state
    means a prior attempt already tore it down: skip the destroy so the run
    converges instead of failing on refresh."""
    pre = owned(state_addresses(source, root), targets)
    if not pre:
        print(f"{root}: nothing owned by this stage left in state; destroy skipped", flush=True)
        return 0, 0
    subprocess.run(
        ["tofu", f"-chdir={root}", "destroy", "-no-color", "-input=false", "-auto-approve",
         *[arg for target in targets or () for arg in ("-target", target)]],
        cwd=source, check=True,
    )
    post = owned(state_addresses(source, root), targets)
    return len(pre), len(post)


def print_destroy_markers(pre, post):
    """Line-anchor the markers regardless of how the previous tool ended its output."""
    sys.stdout.write("\n")
    print(f"CONFIG0_DESTROY_PRE_STATE_COUNT={pre}")
    print(f"CONFIG0_DESTROY_POST_STATE_COUNT={post}", flush=True)


def destroy(stage, source):
    addon = _installer(source)
    args = addon.parse_args(_installer_argv("deploy"))
    addon.require_tofu()
    addon.prepare_root(args, "infra/deploy", "deploy", addon.deploy_tfvars(args))
    if stage == "ecr":
        targets = ("module.ecr",)
    else:
        # The deploy stage owns every deploy module except module.ecr, which
        # the matching ecr stage created and removes after image cleanup.
        targets = (
            "module.hub_executor_poweruser",
            "module.hub_setup",
            "module.run_folder",
            "module.run_folder_apply",
            "module.run_folder_destroy",
            "module.openci_tf",
        )
    pre, post = destroy_root(source, "infra/deploy", targets)
    if stage == "deploy":
        addon.prepare_root(
            args, "infra/foundation", "foundation",
            [f"aws_region={args.region}", f"name_prefix={args.project_name}"],
        )
        foundation_pre, foundation_post = destroy_root(source, "infra/foundation")
        pre, post = pre + foundation_pre, post + foundation_post
        import boto3

        ssm = boto3.client("ssm", region_name=env("OPENCI_TF_REGION"))
        try:
            ssm.delete_parameter(Name=_outputs_param())
        except ssm.exceptions.ParameterNotFound:
            print(f"SSM parameter {_outputs_param()} already absent", flush=True)
    print_destroy_markers(pre, post)


def main():
    stage = env("STAGE")
    if stage not in STAGES:
        raise ValueError(f'STAGE "{stage}" not supported; expected one of {STAGES}')
    method = env("METHOD", "create")
    if method not in ("create", "destroy"):
        raise ValueError(f'METHOD "{method}" not supported; expected create|destroy')
    print(f"openci-tf addon tofu stage={stage} method={method}", flush=True)
    workdir = os.getcwd()
    install_tofu(env("TOFU_VERSION"), os.path.join(workdir, "bin"))
    source = checkout(env("OPENCI_TF_REPO_URL"), env("OPENCI_TF_GIT_REF"),
                      os.path.join(workdir, "openci-tf"))
    (create if method == "create" else destroy)(stage, source)
    print(f"openci-tf addon tofu stage={stage} method={method} complete", flush=True)


if __name__ == "__main__":
    main()

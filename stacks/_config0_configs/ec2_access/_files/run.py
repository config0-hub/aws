"""EC2 access grant: one IAM role for one grantee on one EC2 instance.

One grant is one internal project, c0-access-<grant id>, and this stack runs
once for it. It serves two target kinds: ec2 (session, port_forward, ssh) and
ec2_windows (rdp); target_kind picks the level set. The ec2-access execgroup
creates the role config0-access-<grant id>, trusted by config0-executor-remote
for the grantee only until end_time, with one inline policy for the level,
scoped to the instance. The tf_executor write-back records the access_grant row
after a successful apply, so the row's existence proves the role exists. Names
and row fields follow the CON-11 contract (ops work-log
2026-09-24/con-11-access-requests/contract.md, section 2b). The project destroy
removes the role; nothing here deletes one.
"""

from datetime import datetime
import re

from config0_publisher.terraform import TFConstructor

# target_kind -> level set. Fixed per stack version; the ec2-access execgroup's
# access_policy module carries the statements per level.
KIND_LEVELS = {
    "ec2": ("session", "port_forward", "ssh"),
    "ec2_windows": ("rdp",),
}

GRANT_ID_RE = re.compile(r"^[0-9a-f]{32}\Z")

# The AWS name rule of the target id this stack puts in the IAM policy; saas-api
# refuses the same shapes (AccessRequestCreate), so a typed "*" or an ARN
# fragment never widens the grant past the one target.
# EC2: "i-" and 8 or 17 hex characters
# (https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/resource-ids.html).
INSTANCE_ID_RE = re.compile(r"^i-(?:[0-9a-f]{8}|[0-9a-f]{17})\Z")

END_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _check_grant(stack):
    if stack.level not in KIND_LEVELS[stack.target_kind]:
        raise ValueError(f'level "{stack.level}" is not a {stack.target_kind} level; '
                         f'{stack.target_kind} levels are {", ".join(KIND_LEVELS[stack.target_kind])}')
    if not GRANT_ID_RE.match(stack.grant_id):
        raise ValueError(f'grant_id must be 32 lowercase hex, got "{stack.grant_id}"')
    # UTC ISO 8601, second precision, Z suffix; strptime raises on anything else.
    datetime.strptime(stack.end_time, END_TIME_FORMAT)
    if not INSTANCE_ID_RE.match(stack.instance_id):
        raise ValueError(f'instance_id must be "i-" and 8 or 17 lowercase hex, got "{stack.instance_id}"')


def run(stackargs):

    stack = newStack(stackargs)

    stack.parse.add_required(key="grant_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="grantee_owner_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="target_kind",
                             types="str",
                             choices=["ec2", "ec2_windows"])

    # every level of both kinds; _check_grant holds each kind to its own set
    stack.parse.add_required(key="level",
                             tags="tfvar",
                             types="str",
                             choices=["session", "port_forward", "ssh", "rdp"])

    stack.parse.add_required(key="end_time",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="instance_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="aws_default_region",
                             tags="tfvar,db,resource,tf_exec_env",
                             types="str")

    stack.parse.add_required(key="aws_account_id",
                             tags="tfvar",
                             types="str")

    stack.add_execgroup("config0-hub:::aws::ec2-access",
                        "tf_execgroup")

    stack.add_substack("config0-hub:::config0_core::tf_executor")

    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    _check_grant(stack)

    stack.set_variable("timeout", 600)

    stack.verify_variables()

    role_name = f"config0-access-{stack.grant_id}"

    tf = TFConstructor(stack=stack,
                       provider="aws",
                       execgroup_name=stack.tf_execgroup.name,
                       resource_name=role_name,
                       resource_type="access_grant")

    tf.include(values={
        "grant_id": stack.grant_id,
        "grantee_owner_id": stack.grantee_owner_id,
        "level": stack.level,
        "end_time": stack.end_time,
        "role_name": role_name,
        "role_arn": f"arn:aws:iam::{stack.aws_account_id}:role/{role_name}",
        "target_kind": stack.target_kind,
        "target_name": stack.instance_id,
        "instance_id": stack.instance_id,
        "aws_account_id": stack.aws_account_id,
        "region": stack.aws_default_region,
        "stack_fqn": stack.stackargs["stack"],
    })

    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()

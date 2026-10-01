"""ECS access grant: one IAM role for one grantee to exec into one ECS service.

One grant is one internal project, c0-access-<grant id>, and this stack runs
once for it. The ecs-access execgroup creates the role
config0-access-<grant id>, trusted by config0-executor-remote for the grantee
only until end_time, with one inline policy for ECS Exec in the service's
cluster. The tf_executor write-back records the access_grant row after a
successful apply, so the row's existence proves the role exists. Names and row
fields follow the CON-11 contract (ops work-log
2026-09-24/con-11-access-requests/contract.md, section 2b). The project destroy
removes the role; nothing here deletes one.
"""

from datetime import datetime
import re

from config0_publisher.terraform import TFConstructor

TARGET_KIND = "ecs"

GRANT_ID_RE = re.compile(r"^[0-9a-f]{32}\Z")

# The AWS name rule of the target id this stack puts in the IAM policy; saas-api
# refuses the same shapes (AccessRequestCreate), so a typed "*" or an ARN
# fragment never widens the grant past the one target.
# ECS clusterName and serviceName: up to 255 letters, digits, underscores and
# hyphens (https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_CreateCluster.html,
# https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_CreateService.html).
ECS_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,255}\Z")

END_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _check_grant(stack):
    if not GRANT_ID_RE.match(stack.grant_id):
        raise ValueError(f'grant_id must be 32 lowercase hex, got "{stack.grant_id}"')
    # UTC ISO 8601, second precision, Z suffix; strptime raises on anything else.
    datetime.strptime(stack.end_time, END_TIME_FORMAT)
    for field in ("ecs_cluster", "ecs_service"):
        value = getattr(stack, field)
        if not ECS_NAME_RE.match(value):
            raise ValueError(f'{field} must be up to 255 letters, digits, underscores or '
                             f'hyphens, got "{value}"')


def run(stackargs):

    stack = newStack(stackargs)

    stack.parse.add_required(key="grant_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="grantee_owner_id",
                             tags="tfvar",
                             types="str")

    # level -> statements; the ecs-access execgroup's access_policy module
    # carries the statements per level.
    stack.parse.add_required(key="level",
                             tags="tfvar",
                             types="str",
                             choices=["exec"])

    stack.parse.add_required(key="end_time",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="ecs_cluster",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="ecs_service",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="aws_default_region",
                             tags="tfvar,db,resource,tf_exec_env",
                             types="str")

    stack.parse.add_required(key="aws_account_id",
                             tags="tfvar",
                             types="str")

    stack.add_execgroup("config0-hub:::aws::ecs-access",
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
        "target_kind": TARGET_KIND,
        "target_name": f"{stack.ecs_cluster}/{stack.ecs_service}",
        "ecs_cluster": stack.ecs_cluster,
        "ecs_service": stack.ecs_service,
        "aws_account_id": stack.aws_account_id,
        "region": stack.aws_default_region,
        "stack_fqn": stack.stackargs["stack"],
    })

    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()

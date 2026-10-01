"""AWS account access grant: one IAM role for one grantee in one AWS account.

One grant is one internal project, c0-access-<grant id>, and this stack runs
once for it. The aws-account-access execgroup creates the role
config0-access-<grant id>, trusted by config0-executor-remote for the grantee
only until end_time, with the AWS managed policy of the grant's level attached
and, at every level, an inline deny on Config0's Parameter Store secrets.
The tf_executor write-back records the access_grant row after a successful
apply, so the row's existence proves the role exists. Names and row fields
follow the CON-11 contract (ops work-log
2026-09-24/con-11-access-requests/contract.md, section 2b). The project destroy
removes the role; nothing here deletes one.
"""

from datetime import datetime
import re

from config0_publisher.terraform import TFConstructor

TARGET_KIND = "aws_account"

GRANT_ID_RE = re.compile(r"^[0-9a-f]{32}\Z")
END_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _check_grant(stack):
    if not GRANT_ID_RE.match(stack.grant_id):
        raise ValueError(f'grant_id must be 32 lowercase hex, got "{stack.grant_id}"')
    # UTC ISO 8601, second precision, Z suffix; strptime raises on anything else.
    datetime.strptime(stack.end_time, END_TIME_FORMAT)


def run(stackargs):

    stack = newStack(stackargs)

    stack.parse.add_required(key="grant_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="grantee_owner_id",
                             tags="tfvar",
                             types="str")

    # level -> AWS managed policy; the aws-account-access execgroup's main.tf
    # carries the policy ARN per level.
    stack.parse.add_required(key="level",
                             tags="tfvar",
                             types="str",
                             choices=["read_only", "view_only", "power_user",
                                      "admin", "security_audit", "billing"])

    stack.parse.add_required(key="end_time",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="aws_default_region",
                             tags="tfvar,db,resource,tf_exec_env",
                             types="str")

    stack.parse.add_required(key="aws_account_id",
                             tags="tfvar",
                             types="str")

    stack.add_execgroup("config0-hub:::aws::aws-account-access",
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
        "target_name": stack.aws_account_id,
        "aws_account_id": stack.aws_account_id,
        "region": stack.aws_default_region,
        "stack_fqn": stack.stackargs["stack"],
    })

    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()

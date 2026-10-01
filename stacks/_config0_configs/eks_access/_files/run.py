"""EKS access grant: one IAM role for one grantee on one EKS cluster.

One grant is one internal project, c0-access-<grant id>, and this stack runs
once for it. The eks-access execgroup creates the role
config0-access-<grant id>, trusted by config0-executor-remote for the grantee
only until end_time, with one EKS access entry and one policy association at
the grant's level. The tf_executor write-back records the access_grant row
after a successful apply, so the row's existence proves the role exists.
Names and row fields follow the CON-11 contract (ops work-log
2026-09-24/con-11-access-requests/contract.md). The project destroy removes
the role; nothing here deletes one.
"""

from datetime import datetime
import re

from config0_publisher.terraform import TFConstructor

TARGET_KIND = "eks"

# level -> scope. Fixed per stack version; the eks-access execgroup's main.tf
# carries the same table with the EKS access policy per level.
LEVEL_SCOPES = {
    "view": "cluster",
    "edit": "namespace",
    "admin": "namespace",
    "cluster_admin": "cluster",
}

GRANT_ID_RE = re.compile(r"^[0-9a-f]{32}\Z")

# The AWS name rule of the target id this stack puts in the IAM policy; saas-api
# refuses the same shapes (AccessRequestCreate), so a typed "*" or an ARN
# fragment never widens the grant past the one target.
# EKS cluster name: 1 to 100, ^[0-9A-Za-z][A-Za-z0-9\-_]*
# (https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateCluster.html).
EKS_CLUSTER_RE = re.compile(r"^[0-9A-Za-z][A-Za-z0-9_-]{0,99}\Z")

END_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _namespaces(stack):
    """The grant's namespaces; at least one for a namespace-scoped level."""
    namespaces = [ns for ns in stack.to_list(stack.access_namespaces) if ns]
    if LEVEL_SCOPES[stack.level] == "namespace" and not namespaces:
        raise ValueError(f'level "{stack.level}" needs at least one namespace in access_namespaces')
    return namespaces


def _check_grant(stack):
    if not GRANT_ID_RE.match(stack.grant_id):
        raise ValueError(f'grant_id must be 32 lowercase hex, got "{stack.grant_id}"')
    # UTC ISO 8601, second precision, Z suffix; strptime raises on anything else.
    datetime.strptime(stack.end_time, END_TIME_FORMAT)
    if not EKS_CLUSTER_RE.match(stack.eks_cluster):
        raise ValueError(f'eks_cluster must be up to 100 letters, digits, hyphens or '
                         f'underscores, a letter or digit first, got "{stack.eks_cluster}"')


def run(stackargs):

    stack = newStack(stackargs)

    stack.parse.add_required(key="grant_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="grantee_owner_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="level",
                             tags="tfvar",
                             types="str",
                             choices=["view", "edit", "admin", "cluster_admin"])

    stack.parse.add_required(key="end_time",
                             tags="tfvar",
                             types="str")

    # comma-separated; the namespaces of an edit or admin grant
    stack.parse.add_required(key="access_namespaces",
                             types="str")

    stack.parse.add_required(key="eks_cluster",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="aws_default_region",
                             tags="tfvar,db,resource,tf_exec_env",
                             types="str")

    stack.parse.add_required(key="aws_account_id",
                             tags="tfvar",
                             types="str")

    stack.add_execgroup("config0-hub:::aws::eks-access",
                        "tf_execgroup")

    stack.add_substack("config0-hub:::config0_core::tf_executor")

    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    _check_grant(stack)

    stack.set_variable("namespaces",
                       _namespaces(stack),
                       tags="tfvar",
                       types="list")

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
        "target_name": stack.eks_cluster,
        "aws_account_id": stack.aws_account_id,
        "region": stack.aws_default_region,
        "stack_fqn": stack.stackargs["stack"],
    })

    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()

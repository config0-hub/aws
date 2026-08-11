"""Fallback Lambda — the polling reconciliation safety net.

Driven by a rate(15 minutes) EventBridge schedule. It scans for still-open
token records (callbackSent = false). Commands that reached a terminal status
complete exactly as the callback would; commands past deadline_epoch fail as
timed out and are cancelled.

The _acquire / _complete / _release_lock helpers are intentionally duplicated
verbatim from the callback Lambda — no shared layer (each handler is a
self-contained zip).

handler() reads env + builds clients, then delegates to reconcile(), which
takes the clients as parameters so the unit tests can drive it with fakes.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# SSM invocation statuses that are NOT terminal — everything else is treated as
# terminal and reconciled, so the fallback closes a run regardless of the exact
# terminal status name. `Cancelling` is transitional (the command is mid-cancel
# and reaches `Cancelled` next) — treating it as terminal would complete the
# token with ResponseCode -1 mid-cancel, so it stays in the non-terminal set.
RUNNING_STATUSES = {"Pending", "InProgress", "Delayed", "Cancelling"}

# See the callback handler: the lock is a re-acquirable LEASE, not a permanent
# boolean. It outlives one 60-second Lambda invocation, expires after 120
# seconds, and is eligible for re-acquisition on the next 15-minute sweep.
LEASE_SECONDS = 120


def _release_lock(table: Any, command_id: str) -> None:
    table.update_item(
        Key={"commandId": command_id},
        UpdateExpression="SET callbackSent = :f",
        ExpressionAttributeValues={":f": False},
    )


def _mark_done(table: Any, command_id: str) -> None:
    """Terminal completion: drop lockedAt while leaving callbackSent=true. This
    is what distinguishes a DONE row (callbackSent=true, no lockedAt — the
    filter and acquire both reject it forever) from an IN-FLIGHT-or-stranded row
    (callbackSent=true WITH lockedAt — re-acquirable once the lease goes stale)."""
    table.update_item(
        Key={"commandId": command_id},
        UpdateExpression="REMOVE lockedAt",
    )


def _acquire(table: Any, command_id: str, now: int | None = None) -> str | None:
    """Conditionally acquire the lease and flip callbackSent -> true, stamping
    lockedAt=now. Returns the taskToken on a win, or None if another worker
    holds a live lease / the record is not acquirable. attribute_exists guards
    against a missing item (a missing item is never acquired and nothing is
    created); the lease is re-acquirable when it was never held, was released,
    or is older than LEASE_SECONDS."""
    if now is None:
        now = int(time.time())
    cutoff = now - LEASE_SECONDS
    try:
        resp = table.update_item(
            Key={"commandId": command_id},
            UpdateExpression="SET callbackSent = :t, lockedAt = :now",
            ConditionExpression=(
                "attribute_exists(commandId) AND "
                "(attribute_not_exists(callbackSent) OR callbackSent = :f OR lockedAt < :cutoff)"
            ),
            ExpressionAttributeValues={":t": True, ":f": False, ":now": now, ":cutoff": cutoff},
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return None
        raise
    return resp["Attributes"]["taskToken"]


def _complete(
    sfn: Any, ssm: Any, table: Any, command_id: str, instance_id: str, task_token: str, path: str
) -> None:
    """Read the command's exit code and release the SFN task token. On
    TaskDoesNotExist/TaskTimedOut the token was already consumed or the task
    timed out — leave callbackSent=true, done. On any other ClientError or on a
    transient BotoCoreError (EndpointConnectionError/ReadTimeout/…), release the
    lease so a later pass re-acquires, and re-raise so the run retries."""
    try:
        inv = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        exit_code = inv["ResponseCode"]
        logger.info("SENDTASK path=%s commandId=%s exit_code=%s", path, command_id, exit_code)
        sfn.send_task_success(
            taskToken=task_token,
            output=json.dumps({"exit_code": exit_code, "command_id": command_id}),
        )
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("TaskDoesNotExist", "TaskTimedOut"):
            # Token already consumed / task timed out — this row is done. Drop
            # the lease so it is never re-acquired.
            _mark_done(table, command_id)
            return
        _release_lock(table, command_id)
        raise
    except BotoCoreError:
        _release_lock(table, command_id)
        raise
    _mark_done(table, command_id)


def _reconcile_one(sfn: Any, ssm: Any, table: Any, item: dict, now: int | None = None) -> None:
    if now is None:
        now = int(time.time())
    command_id = item["commandId"]
    instance_id = item["instanceId"]
    try:
        inv = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "InvocationDoesNotExist":
            raise
        # A command with no invocation is not terminal. Before its deadline it
        # remains eligible for a later pass; after its deadline it follows the
        # same timeout closure as an explicitly running command.
        inv = None
    if inv is not None:
        status = inv["Status"]
        if status not in RUNNING_STATUSES:
            task_token = _acquire(table, command_id, now)
            if task_token is None:
                logger.info("SKIP path=fallback commandId=%s (already completed)", command_id)
                return
            _complete(sfn, ssm, table, command_id, instance_id, task_token, "fallback")
            return
    deadline_epoch = item["deadline_epoch"]
    if now < deadline_epoch:
        return
    task_token = _acquire(table, command_id, now)
    if task_token is None:
        logger.info("SKIP path=overdue commandId=%s (already completed)", command_id)
        return
    logger.info(
        "SENDTASK path=overdue commandId=%s deadline_epoch=%s",
        command_id,
        deadline_epoch,
    )
    try:
        sfn.send_task_failure(
            taskToken=task_token,
            error="SsmCommandTimedOut",
            cause=f"SSM command exceeded deadline_epoch={deadline_epoch}",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in ("TaskDoesNotExist", "TaskTimedOut"):
            _release_lock(table, command_id)
            raise
    except BotoCoreError:
        _release_lock(table, command_id)
        raise
    try:
        ssm.cancel_command(CommandId=command_id, InstanceIds=[instance_id])
    except (ClientError, BotoCoreError):
        _release_lock(table, command_id)
        raise
    _mark_done(table, command_id)


def reconcile(sfn: Any, ssm: Any, table: Any, now: int | None = None) -> None:
    # ponytail: one poison record raising an unexpected error aborts the whole
    # pass, stalling the safety net until it clears. Acceptable for a
    # low-volume standalone tool and it keeps the fail-loud discipline; add
    # per-item isolation if a stuck record ever wedges the reconciler.
    if now is None:
        now = int(time.time())
    cutoff = now - LEASE_SECONDS
    # Admit both open records (callbackSent false/absent) AND rows whose lease
    # has gone stale (an acquirer died mid-flight leaving callbackSent=true) —
    # otherwise a stranded lease never reappears in the scan and can never be
    # re-acquired, defeating the fallback.
    scan_kwargs = {
        "FilterExpression": (
            "attribute_exists(taskToken) AND "
            "(callbackSent = :f OR attribute_not_exists(callbackSent) OR lockedAt < :cutoff)"
        ),
        "ExpressionAttributeValues": {":f": False, ":cutoff": cutoff},
    }
    last_key = None
    while True:
        if last_key is not None:
            scan_kwargs["ExclusiveStartKey"] = last_key
        resp = table.scan(**scan_kwargs)
        for item in resp.get("Items", []):
            _reconcile_one(sfn, ssm, table, item, now)
        last_key = resp.get("LastEvaluatedKey")
        if last_key is None:
            break


def handler(event: dict, context: Any) -> None:
    region = os.environ["AWS_REGION"]
    table_name = os.environ["TOKEN_TABLE"]

    ssm = boto3.client("ssm", region_name=region)
    sfn = boto3.client("stepfunctions", region_name=region)
    table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    reconcile(sfn, ssm, table, int(time.time()))

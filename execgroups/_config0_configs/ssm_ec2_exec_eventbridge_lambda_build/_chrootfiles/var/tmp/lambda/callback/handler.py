"""Callback Lambda — the fast, event-driven completion path.

EventBridge delivers the SSM "EC2 Command Invocation Status-change
Notification" for a terminal status. This handler conditionally acquires the
token record (callbackSent false -> true), reads the command's exit code, and
releases the SFN task with SendTaskSuccess. The Choice state in the ASL decides
Succeeded vs Failed from that exit_code.

The _acquire / _complete / _release_lock helpers are intentionally duplicated
verbatim in the fallback Lambda — no shared layer (each handler is a
self-contained zip).

handler() reads env + builds clients, then delegates to process_event(), which
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

# The lock on a token record is a LEASE, not a permanent boolean. An acquirer
# that dies after acquiring but before completing (a Lambda timeout, or a
# BotoCoreError whose release path itself failed) would otherwise strand
# callbackSent=true forever and hang the SFN. LEASE_SECONDS is comfortably
# above one Lambda max duration (lambda_timeout_seconds = 60), so a live
# invocation cannot have its lease stolen mid-flight. A stranded lease expires
# after 120 seconds and is eligible for re-acquisition on the next 15-minute
# fallback sweep.
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


def process_event(sfn: Any, ssm: Any, table: Any, event: dict, now: int | None = None) -> None:
    detail = event["detail"]
    command_id = detail["command-id"]
    instance_id = detail["instance-id"]
    status = detail["status"]

    task_token = _acquire(table, command_id, now)
    if task_token is None:
        logger.info(
            "SKIP path=callback commandId=%s status=%s (already completed or not acquirable)",
            command_id,
            status,
        )
        return
    # Log the incoming terminal status on the COMPLETING path too (it used to be
    # visible only on the SKIP path, so a completing command's live status never
    # appeared in its own log line).
    logger.info("EVENT path=callback commandId=%s status=%s (acquired)", command_id, status)
    _complete(sfn, ssm, table, command_id, instance_id, task_token, "callback")


def handler(event: dict, context: Any) -> None:
    region = os.environ["AWS_REGION"]
    table_name = os.environ["TOKEN_TABLE"]

    ssm = boto3.client("ssm", region_name=region)
    sfn = boto3.client("stepfunctions", region_name=region)
    table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    process_event(sfn, ssm, table, event, int(time.time()))

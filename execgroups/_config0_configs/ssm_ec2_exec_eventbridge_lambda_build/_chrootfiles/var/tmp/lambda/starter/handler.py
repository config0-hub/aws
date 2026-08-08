"""Starter Lambda — invoked by Step Functions with waitForTaskToken.

It holds the ONLY copy of the SFN task token. It fires the SSM command, stores
the token in DynamoDB keyed by the returned CommandId (so the callback/fallback
Lambdas can release it later), and returns. It never returns the token to the
state machine and never travels it to the EC2 box.

Boundary rule: if SendCommand or PutItem fails, nothing downstream will ever
release the task — so this handler fails the task loud with the token it holds
before re-raising.

handler() reads env + builds clients, then delegates to run_starter(), which
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


def run_starter(
    ssm: Any,
    table: Any,
    sfn: Any,
    *,
    event: dict,
    bucket: str,
    ssm_log_group_name: str,
    now_epoch: int,
) -> dict:
    task_token = event["TaskToken"]
    try:
        instance_id = event["instance_id"]
        script = event["script"]
        timeout_seconds = int(event["timeout_seconds"])
        execution_arn = event["executionArn"]

        sent = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            TimeoutSeconds=timeout_seconds,
            Parameters={
                "commands": [script],
                "executionTimeout": [str(timeout_seconds)],
            },
            CloudWatchOutputConfig={
                "CloudWatchLogGroupName": ssm_log_group_name,
                "CloudWatchOutputEnabled": True,
            },
            OutputS3BucketName=bucket,
            OutputS3KeyPrefix="native-output",
        )
        command_id = sent["Command"]["CommandId"]

        table.put_item(
            Item={
                "commandId": command_id,
                "taskToken": task_token,
                "executionArn": execution_arn,
                "instanceId": instance_id,
                "status": "in_progress",
                "createdAt": now_epoch,
                # TTL exceeds the SFN task timeout so the fallback never loses
                # a row it still needs (timeout + 3600 vs the task's
                # timeout + 600 callback bound).
                "expiresAt": now_epoch + timeout_seconds + 3600,
                "callbackSent": False,
            }
        )
        logger.info(
            "STARTED commandId=%s instanceId=%s executionArn=%s",
            command_id,
            instance_id,
            execution_arn,
        )
        return {"command_id": command_id}
    except (ClientError, BotoCoreError) as exc:
        # The starter holds the only copy of the task token. On an operational
        # AWS error (SendCommand/PutItem), the command was not durably
        # registered, so no callback/fallback will ever release the SFN task —
        # fail it loud now, then re-raise so the error is recorded in
        # CloudWatch. A programmer/data-shape defect (KeyError/ValueError) is
        # NOT masked here; it propagates uncaught.
        logger.exception(
            "starter failed; sending task failure for executionArn=%s",
            event.get("executionArn"),
        )
        sfn.send_task_failure(
            taskToken=task_token,
            error="StarterFailed",
            cause=str(exc)[:32000],
        )
        raise


def handler(event: dict, context: Any) -> dict:
    region = os.environ["AWS_REGION"]
    table_name = os.environ["TOKEN_TABLE"]
    bucket = os.environ["OUTPUT_BUCKET"]
    ssm_log_group_name = os.environ["SSM_LOG_GROUP_NAME"]

    ssm = boto3.client("ssm", region_name=region)
    sfn = boto3.client("stepfunctions", region_name=region)
    table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    return run_starter(
        ssm,
        table,
        sfn,
        event=event,
        bucket=bucket,
        ssm_log_group_name=ssm_log_group_name,
        now_epoch=int(time.time()),
    )

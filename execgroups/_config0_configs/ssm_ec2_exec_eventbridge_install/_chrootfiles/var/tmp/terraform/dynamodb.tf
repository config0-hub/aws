# ---------------------------------------------------------------------------
# Token-map table. One row per SSM command the starter fires: it records the
# Step Functions task token (server-side — the token never travels to the EC2
# box in v2) keyed by the SSM CommandId, so the callback/fallback Lambdas can
# find the token when the command reaches a terminal status.
#
# PK is commandId. Only the key attribute is declared — DynamoDB requires that
# every declared attribute be indexed, so the non-key attributes (taskToken,
# executionArn, instanceId, status, createdAt, callbackSent) are written
# schemalessly and never declared here. TTL on expiresAt reaps stale rows; the
# starter sets expiresAt = now + timeout + 3600 so the record always outlives
# the SFN task timeout and the fallback never loses a row it still needs.
# ---------------------------------------------------------------------------

resource "aws_dynamodb_table" "tokens" {
  name         = local.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "commandId"

  attribute {
    name = "commandId"
    type = "S"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  tags = local.tags
}

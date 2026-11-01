#!/bin/bash
# agent_server's user data on every server: the SSM agent registers within
# minutes of launch. The Noble AMI's agent (the amazon-ssm-agent snap) asks for
# credentials once, about 15 s after boot. When the new instance profile has not
# reached the instance yet, it falls back to Default Host Management and makes
# no call with the instance role for about half an hour. So wait until the
# instance metadata service serves the instance-profile credentials (300 s at
# most), then restart the agent so it registers at once. The credentials are
# only checked, never printed or written. No secret lives here. Never add set -x.
set -euo pipefail

python3 -c '
import json, sys, time, urllib.error, urllib.request

IMDS = "http://169.254.169.254/latest"
DEADLINE = time.monotonic() + 300


def get(path, token):
    request = urllib.request.Request(IMDS + path, headers={"X-aws-ec2-metadata-token": token})
    return urllib.request.urlopen(request, timeout=5).read().decode()


while True:
    token = urllib.request.urlopen(urllib.request.Request(
        IMDS + "/api/token", method="PUT",
        headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"}), timeout=5).read().decode()
    try:
        roles = get("/meta-data/iam/security-credentials/", token).split()
        if roles and json.loads(get("/meta-data/iam/security-credentials/" + roles[0], token))["Code"] == "Success":
            break
    except urllib.error.HTTPError as error:
        # No instance-profile credentials yet: the metadata service answers 404.
        if error.code != 404:
            raise
    if time.monotonic() >= DEADLINE:
        sys.exit("ssm_agent_register.sh: the instance metadata service served no instance-profile "
                 "credentials within 300 s; the SSM agent was not restarted")
    time.sleep(5)
'
snap restart amazon-ssm-agent

#!/bin/bash
# agent_server's user data with Tailscale on: join the customer's tailnet at
# first boot. No secret lives here, since user data stays readable on the
# instance. The instance role reads the tailscale_join input variable set from
# its SSM path below. The secret exists only in this shell's variable while
# tailscale up runs, and is never written to disk. Never add set -x.
set -euo pipefail

# Nothing on the image is assumed: curl fetches the installer and boto3 reads
# the parameter with the instance role. First-boot apt timers can hold the
# dpkg lock, so apt waits for it instead of failing.
echo 'DPkg::Lock::Timeout "300";' > /etc/apt/apt.conf.d/90config0-lock-timeout
apt-get update
apt-get install -y curl python3-boto3
curl -fsSL https://tailscale.com/install.sh | sh

# The set is one base64 JSON blob, and each value in it is base64 again.
TS_OAUTH_CLIENT_SECRET="$(python3 -c '
import base64, json, sys
import boto3
ssm = boto3.client("ssm", region_name=sys.argv[1])
blob = ssm.get_parameter(Name=sys.argv[2], WithDecryption=True)["Parameter"]["Value"]
print(base64.b64decode(json.loads(base64.b64decode(blob))["TS_OAUTH_CLIENT_SECRET"]).decode())
' "${region}" "${join_parameter_path}")"

# The OAuth client secret as the auth key: tag-owned, non-ephemeral so a
# stopped server keeps its device, preauthorized.
tailscale up \
  --auth-key="$${TS_OAUTH_CLIENT_SECRET}?ephemeral=false&preauthorized=true" \
  --advertise-tags="${tailscale_tag}" \
  --hostname="${hostname}" \
  --ssh
unset TS_OAUTH_CLIENT_SECRET

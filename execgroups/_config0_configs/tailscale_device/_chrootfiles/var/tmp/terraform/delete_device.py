"""Delete one Tailscale device on destroy: DELETE /api/v2/device/{node_id}.

Runs as the destroy-time provisioner of terraform_data.device, in the engine,
with the python3 the engine's own SSM reader uses. The admin OAuth client is in
the environment as TAILSCALE_OAUTH_CLIENT_ID and TAILSCALE_OAUTH_CLIENT_SECRET,
sourced by the engine before tofu runs. TAILSCALE_BASE_URL, when set, moves the
API the same way it moves the provider's. Any answer but 200, a 404 included,
exits non-zero with the status, so the destroy stops and the server stays.
Never print the token or the client secret.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

api = os.environ.get("TAILSCALE_BASE_URL", "https://api.tailscale.com").rstrip("/") + "/api/v2"
node_id = os.environ["NODE_ID"]

form = urllib.parse.urlencode({
    "client_id": os.environ["TAILSCALE_OAUTH_CLIENT_ID"],
    "client_secret": os.environ["TAILSCALE_OAUTH_CLIENT_SECRET"],
}).encode()
try:
    with urllib.request.urlopen(urllib.request.Request(f"{api}/oauth/token", data=form), timeout=60) as response:
        token = json.load(response)["access_token"]
except urllib.error.HTTPError as err:
    sys.exit(f"Tailscale OAuth token request answered HTTP {err.code}; device {node_id} was not deleted")

request = urllib.request.Request(
    f"{api}/device/{urllib.parse.quote(node_id, safe='')}",
    method="DELETE",
    headers={"Authorization": f"Bearer {token}"},
)
try:
    with urllib.request.urlopen(request, timeout=60) as response:
        status = response.status
except urllib.error.HTTPError as err:
    status = err.code
if status != 200:
    sys.exit(f"DELETE /api/v2/device/{node_id} answered HTTP {status}; the device, the server and their rows stay")
print(f"deleted Tailscale device {node_id}")

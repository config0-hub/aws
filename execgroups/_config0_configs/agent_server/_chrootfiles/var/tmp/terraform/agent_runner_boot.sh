#!/bin/bash
# agent_server's user data on every server: install and start the runner daemon
# at first boot (R1-5). daemon_pkg_url is the presigned link the agent_server
# run asked saas-api for under its run token; it expires, so this is the one
# fetch. cloud-init runs user data at the first boot only; later boots start the
# installed copy through systemd. Delete and re-add a server to take a newer
# release. No secret lives here. Never add set -x.
set -euo pipefail

# First-boot apt timers can hold the dpkg lock, so apt waits for it.
echo 'DPkg::Lock::Timeout "300";' > /etc/apt/apt.conf.d/90config0-lock-timeout
apt-get update
apt-get install -y curl

# Node 22 from NodeSource: Claude Code needs Node 22 or later and pi 0.99 needs
# 22.19 or later, and Noble's own nodejs is 18.19. NodeSource's nodejs carries npm.
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

# The two agent CLIs on the system PATH, readable by config0-agent.
npm install -g "@anthropic-ai/claude-code@${claude_version}" "${pi_package}@${pi_version}"

DIST=/opt/config0-agent-runner-dist
mkdir -p "$${DIST}"
curl -fsSL -o "$${DIST}/daemon.zip" "${daemon_pkg_url}"
# zipfile drops the exec bits, so install.sh runs through bash.
python3 -m zipfile -e "$${DIST}/daemon.zip" "$${DIST}"

export CONFIG0_AGENT_QUEUE_URL="${queue_url}"
export CONFIG0_AGENT_REGION="${region}"
export CONFIG0_AGENT_PRUNE_AGE_DAYS="${prune_age_days}"
%{ if max_concurrent != null ~}
export CONFIG0_AGENT_MAX_CONCURRENT="${max_concurrent}"
%{ endif ~}
# install.sh writes /etc/config0-agent-runner.env and the systemd unit, then enables it.
bash "$${DIST}/install.sh"

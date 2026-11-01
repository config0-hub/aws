# The Tailscale add-on's install check. It reads the user's tailnet policy and
# device list and writes nothing in the tailnet: no tailscale_* resource lives
# here. The user owns the policy; the add-on card shows the entries below.

data "tailscale_acl" "policy" {}

# A successful read proves the admin client's device scope.
data "tailscale_devices" "all" {}

locals {
  policy    = jsondecode(data.tailscale_acl.policy.json)
  grants    = try(local.policy.grants, [])
  ssh_rules = try(local.policy.ssh, [])

  tag_owners = try(local.policy.tagOwners[var.tailscale_tag], [])

  # Literal matches of the entries the card shows. Equivalent legacy `acls`
  # entries are not accepted.
  member_to_tag = [
    for grant in local.grants : grant
    if contains(try(grant.src, []), "autogroup:member")
    && contains(try(grant.dst, []), var.tailscale_tag)
    && contains(try(grant.ip, []), "*")
  ]
  tag_to_tag = [
    for grant in local.grants : grant
    if contains(try(grant.src, []), var.tailscale_tag)
    && contains(try(grant.dst, []), var.tailscale_tag)
    && contains(try(grant.ip, []), "*")
  ]
  ssh_accept = [
    for rule in local.ssh_rules : rule
    if try(rule.action, "") == "accept"
    && contains(try(rule.src, []), "autogroup:member")
    && contains(try(rule.dst, []), var.tailscale_tag)
    && contains(try(rule.users, []), var.ssh_login)
  ]
}

# Lives in state only. Its preconditions fail the plan, naming the missing entry.
resource "terraform_data" "policy_check" {
  input = {
    tailscale_tag = var.tailscale_tag
    ssh_login     = var.ssh_login
  }

  lifecycle {
    precondition {
      condition     = length(local.tag_owners) > 0
      error_message = "The tailnet policy has no tagOwners[\"${var.tailscale_tag}\"] entry. Add \"tagOwners\": {\"${var.tailscale_tag}\": [\"autogroup:admin\"]}."
    }
    precondition {
      condition     = length(local.member_to_tag) > 0
      error_message = "The tailnet policy has no member-to-tag grant. Add {\"src\": [\"autogroup:member\"], \"dst\": [\"${var.tailscale_tag}\"], \"ip\": [\"*\"]} to \"grants\"."
    }
    precondition {
      condition     = length(local.tag_to_tag) > 0
      error_message = "The tailnet policy has no tag-to-tag grant. Add {\"src\": [\"${var.tailscale_tag}\"], \"dst\": [\"${var.tailscale_tag}\"], \"ip\": [\"*\"]} to \"grants\"."
    }
    precondition {
      condition     = length(local.ssh_accept) > 0
      error_message = "The tailnet policy has no ssh accept rule for ${var.ssh_login}. Add {\"action\": \"accept\", \"src\": [\"autogroup:member\"], \"dst\": [\"${var.tailscale_tag}\"], \"users\": [\"${var.ssh_login}\"]} to \"ssh\"."
    }
  }
}

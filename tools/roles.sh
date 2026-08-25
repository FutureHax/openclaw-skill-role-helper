#!/usr/bin/env bash
# Game-access role helper for Zordon OpenClaw.
# Only roles in catalog.json may be added or removed.
#
# Usage:
#   roles.sh catalog
#   roles.sh status <caller_discord_id>
#   roles.sh lookup <query>
#   roles.sh add <caller_discord_id> <role_id_or_label>
#   roles.sh remove <caller_discord_id> <role_id_or_label>
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIB="${ROOT}/lib"
CATALOG_FILE="${ROOT}/catalog.json"

# Load OpenClaw env when present (VPS)
if [[ -f "${HOME}/.openclaw/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${HOME}/.openclaw/.env"
  set +a
fi

ACTION="${1:-}"
if [[ -z "$ACTION" ]]; then
  echo '{"error":"Usage: roles.sh catalog|status|lookup|add|remove ..."}' >&2
  exit 1
fi
shift || true

json_error() {
  MSG="$1" python3 -c 'import json,os; print(json.dumps({"error": os.environ["MSG"]}))' >&2
  exit 1
}

# Fail closed on catalog before any Discord call
if [[ ! -f "$CATALOG_FILE" ]]; then
  json_error "catalog missing"
fi

run_py() {
  # Read a Python program from stdin (heredoc). Do not use for -c one-liners.
  PYTHONPATH="${LIB}${PYTHONPATH:+:$PYTHONPATH}" python3 -
}

run_py_c() {
  PYTHONPATH="${LIB}${PYTHONPATH:+:$PYTHONPATH}" python3 -c "$1"
}

detect_guild_id() {
  if [[ -n "${DISCORD_GUILD_ID:-}" ]]; then
    echo "$DISCORD_GUILD_ID"
    return 0
  fi
  python3 -c "
import json, sys
try:
    with open('${HOME}/.openclaw/openclaw.json') as f:
        c = json.load(f)
    guilds = c.get('channels',{}).get('discord',{}).get('guilds',{})
    print(list(guilds.keys())[0])
except Exception:
    sys.exit(1)
" 2>/dev/null || echo "1296607220221345835"
}

discord_request() {
  local method="$1"
  local endpoint="$2"
  local data="${3:-}"

  local curl_args=(
    -s --connect-timeout 5 --max-time 15
    -X "$method"
    -H "Authorization: Bot ${DISCORD_BOT_TOKEN}"
    -H "Content-Type: application/json"
    -H "Accept: application/json"
    -w "\n%{http_code}"
  )
  if [[ -n "$data" ]]; then
    curl_args+=(-d "$data")
  fi

  local response
  response=$(curl "${curl_args[@]}" "https://discord.com/api/v10${endpoint}" 2>&1)

  local http_code body
  http_code=$(echo "$response" | tail -1)
  body=$(echo "$response" | sed '$d')

  if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
    echo "$body"
    return 0
  fi

  HTTP_CODE="$http_code" BODY="$body" python3 -c '
import json, os
body = os.environ.get("BODY", "")
try:
    details = json.loads(body) if body else body
except Exception:
    details = body
payload = {"error": "Discord API error", "status": int(os.environ["HTTP_CODE"]), "details": details}
if int(os.environ["HTTP_CODE"]) == 403:
    payload["message"] = (
        "Zordon cannot assign that game role yet: the bot role must sit above "
        "the game role in Server Settings > Roles. Ask an admin to fix hierarchy."
    )
print(json.dumps(payload, indent=2))
'
  return 1
}

case "$ACTION" in
  catalog)
    run_py <<'PY'
import json, sys
from catalog import flatten_roles, load_catalog
catalog = load_catalog()
rows = flatten_roles(catalog)
print(json.dumps({"ok": True, "roles": rows, "count": len(rows)}, indent=2))
PY
    ;;

  lookup)
    QUERY="${1:?Usage: roles.sh lookup <query>}"
    QUERY="$QUERY" run_py <<'PY'
import json, os
from catalog import load_catalog
from resolve import lookup_catalog

catalog = load_catalog()
result = lookup_catalog(catalog, os.environ["QUERY"])
# Friendly copy pointing at /get-roles
matches = result.get("matches") or []
if result.get("unique"):
    role = result["unique"]
    channel = role.get("generalChannelId") or ""
    msg = (
        f"You need the **{role['label']}** game role for access."
        + (f" General chat: <#{channel}>." if channel else "")
        + " I can add it for you, or use `/get-roles` to manage game roles yourself."
    )
    result["message"] = msg
elif result.get("error") == "ambiguous match":
    names = ", ".join(f"**{m['label']}**" for m in matches)
    result["message"] = f"Several game roles match: {names}. Which one?"
elif result.get("error") == "that is not a self-serve game role":
    result["message"] = (
        "That is not a self-serve game role. "
        "I only manage curated game-access roles. Use `/get-roles` to browse those."
    )
else:
    result["message"] = (
        "No matching self-serve game role. Use `/get-roles` to browse available game roles."
    )
print(json.dumps(result, indent=2))
PY
    ;;

  status)
    CALLER_ID="${1:?Usage: roles.sh status <caller_discord_id>}"
    if [[ -z "${DISCORD_BOT_TOKEN:-}" ]]; then
      json_error "DISCORD_BOT_TOKEN is not set"
    fi
    GUILD_ID="$(detect_guild_id)"
    MEMBER_JSON=$(discord_request GET "/guilds/${GUILD_ID}/members/${CALLER_ID}") || exit 1
    MEMBER_JSON="$MEMBER_JSON" CALLER_ID="$CALLER_ID" run_py <<'PY'
import json, os
from catalog import filter_member_roles_to_catalog, load_catalog

member = json.loads(os.environ["MEMBER_JSON"])
catalog = load_catalog()
# Discord returns roles as a list of snowflake strings
member_roles = member.get("roles") or []
game_roles = filter_member_roles_to_catalog(member_roles, catalog)
print(json.dumps({
    "ok": True,
    "userId": os.environ["CALLER_ID"],
    "gameRoles": game_roles,
    "count": len(game_roles),
    "message": (
        "Your game-access roles: " + ", ".join(f"**{r['label']}**" for r in game_roles)
        if game_roles else
        "You have no curated game-access roles yet. Use `/get-roles` or ask me to add one."
    ),
}, indent=2))
PY
    ;;

  add|remove)
    CALLER_ID="${1:?Usage: roles.sh ${ACTION} <caller_discord_id> <role_id_or_label>}"
    ROLE_QUERY="${2:?Usage: roles.sh ${ACTION} <caller_discord_id> <role_id_or_label>}"

    # Gate BEFORE any Discord write (and before requiring token for resolve failures)
    set +e
    GATE_JSON=$(
      CALLER_ID="$CALLER_ID" ROLE_QUERY="$ROLE_QUERY" run_py <<'PY'
import json, os, sys
from catalog import load_catalog
from gates import gate_write

catalog = load_catalog()
result = gate_write(catalog, os.environ["CALLER_ID"], os.environ["ROLE_QUERY"])
print(json.dumps(result))
sys.exit(0 if result.get("ok") else 2)
PY
    )
    GATE_RC=$?
    set -e
    if [[ "$GATE_RC" -ne 0 ]]; then
      echo "$GATE_JSON"
      exit 1
    fi

    if [[ -z "${DISCORD_BOT_TOKEN:-}" ]]; then
      json_error "DISCORD_BOT_TOKEN is not set"
    fi

    GUILD_ID="$(detect_guild_id)"
    ROLE_ID=$(GATE_JSON="$GATE_JSON" run_py_c 'import json,os; print(json.loads(os.environ["GATE_JSON"])["role"]["roleId"])')
    ROLE_LABEL=$(GATE_JSON="$GATE_JSON" run_py_c 'import json,os; print(json.loads(os.environ["GATE_JSON"])["role"]["label"])')
    GENERAL_CH=$(GATE_JSON="$GATE_JSON" run_py_c 'import json,os; print(json.loads(os.environ["GATE_JSON"])["role"].get("generalChannelId") or "")')

    if [[ "$ACTION" == "add" ]]; then
      set +e
      DISCORD_RESP=$(discord_request PUT "/guilds/${GUILD_ID}/members/${CALLER_ID}/roles/${ROLE_ID}")
      DISCORD_RC=$?
      set -e
      if [[ "$DISCORD_RC" -ne 0 ]]; then
        [[ -n "$DISCORD_RESP" ]] && echo "$DISCORD_RESP"
        exit 1
      fi
      GENERAL_CH="$GENERAL_CH" ROLE_LABEL="$ROLE_LABEL" ROLE_ID="$ROLE_ID" CALLER_ID="$CALLER_ID" run_py <<'PY'
import json, os
channel = os.environ.get("GENERAL_CH") or ""
label = os.environ["ROLE_LABEL"]
msg = f"Added **{label}**."
if channel:
    msg += f" You should now see <#{channel}>."
msg += " Use `/get-roles` anytime to manage game roles."
print(json.dumps({
    "ok": True,
    "action": "add",
    "userId": os.environ["CALLER_ID"],
    "roleId": os.environ["ROLE_ID"],
    "label": label,
    "generalChannelId": channel,
    "message": msg,
}, indent=2))
PY
    else
      set +e
      DISCORD_RESP=$(discord_request DELETE "/guilds/${GUILD_ID}/members/${CALLER_ID}/roles/${ROLE_ID}")
      DISCORD_RC=$?
      set -e
      if [[ "$DISCORD_RC" -ne 0 ]]; then
        [[ -n "$DISCORD_RESP" ]] && echo "$DISCORD_RESP"
        exit 1
      fi
      GENERAL_CH="$GENERAL_CH" ROLE_LABEL="$ROLE_LABEL" ROLE_ID="$ROLE_ID" CALLER_ID="$CALLER_ID" run_py <<'PY'
import json, os
channel = os.environ.get("GENERAL_CH") or ""
label = os.environ["ROLE_LABEL"]
msg = f"Removed **{label}**."
if channel:
    msg += f" You may lose access to <#{channel}>."
print(json.dumps({
    "ok": True,
    "action": "remove",
    "userId": os.environ["CALLER_ID"],
    "roleId": os.environ["ROLE_ID"],
    "label": label,
    "generalChannelId": channel,
    "message": msg,
}, indent=2))
PY
    fi
    ;;

  *)
    json_error "Unknown action: ${ACTION}. Valid: catalog, status, lookup, add, remove"
    ;;
esac

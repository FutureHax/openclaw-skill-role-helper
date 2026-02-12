#!/usr/bin/env bash
set -euo pipefail

# Role Helper — look up the Discord role for a game
# Usage: lookup.sh <game_name_or_search>
#
# Queries the Zordon API for matching games, then searches Discord guild
# roles for a matching role name. Returns JSON with match results and a
# formatted message directing the player to #get-roles-here.

SEARCH="${1:?Usage: lookup.sh <game_name_or_search>}"

# ── Validate required env vars ────────────────────────────────────────
for var in ZORDON_API_URL ZORDON_API_KEY DISCORD_BOT_TOKEN; do
  if [[ -z "${!var:-}" ]]; then
    echo "{\"error\":\"${var} is not set\"}" >&2
    exit 1
  fi
done

# ── Constants ─────────────────────────────────────────────────────────
GET_ROLES_CHANNEL_ID="1383948225710522378"
GET_ROLES_CHANNEL_URL="https://discord.com/channels/1296607220221345835/${GET_ROLES_CHANNEL_ID}"
DISCORD_API="https://discord.com/api/v10"

# ── Auto-detect guild ID ─────────────────────────────────────────────
if [[ -z "${DISCORD_GUILD_ID:-}" ]]; then
  DISCORD_GUILD_ID=$(python3 -c "
import json, sys
try:
    with open('$HOME/.openclaw/openclaw.json') as f:
        c = json.load(f)
    guilds = c.get('channels',{}).get('discord',{}).get('guilds',{})
    print(list(guilds.keys())[0])
except:
    sys.exit(1)
" 2>/dev/null) || DISCORD_GUILD_ID="1296607220221345835"
fi

# ── Fetch data ────────────────────────────────────────────────────────
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Fetch games from Zordon API
curl -sfk --connect-timeout 5 --max-time 15 \
  -H "Authorization: Bearer ${ZORDON_API_KEY}" \
  -H "Accept: application/json" \
  "${ZORDON_API_URL}/games" > "$TMPDIR/games.json" 2>/dev/null || echo "[]" > "$TMPDIR/games.json"

# Fetch roles from Discord API
curl -sf --connect-timeout 5 --max-time 15 \
  -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
  -H "Accept: application/json" \
  "${DISCORD_API}/guilds/${DISCORD_GUILD_ID}/roles" > "$TMPDIR/roles.json" 2>/dev/null || echo "[]" > "$TMPDIR/roles.json"

# ── Match game to role ────────────────────────────────────────────────
SEARCH_TERM="$SEARCH" ROLES_CHANNEL_ID="$GET_ROLES_CHANNEL_ID" \
  ROLES_CHANNEL_URL="$GET_ROLES_CHANNEL_URL" \
  GAMES_FILE="$TMPDIR/games.json" ROLES_FILE="$TMPDIR/roles.json" \
  python3 -c "
import json, os, sys

search = os.environ['SEARCH_TERM'].lower().strip()
channel_id = os.environ['ROLES_CHANNEL_ID']
channel_url = os.environ['ROLES_CHANNEL_URL']

# Load API responses
with open(os.environ['GAMES_FILE']) as f:
    games_raw = json.load(f)
with open(os.environ['ROLES_FILE']) as f:
    roles = json.load(f)

# Normalize games (may be list or {games: [...]})
games = games_raw if isinstance(games_raw, list) else games_raw.get('games', [])

# Find matching games (case-insensitive partial match)
matched_games = []
for g in games:
    name = (g.get('name') or g.get('title') or '').lower()
    if search in name or name in search:
        matched_games.append(g)

# Build list of names to match against roles
game_names = [search]
for g in matched_games:
    gn = (g.get('name') or g.get('title') or '').lower()
    if gn and gn not in game_names:
        game_names.append(gn)

# Find matching Discord roles
matched_roles = []
seen_role_ids = set()
for r in roles:
    rname = r.get('name', '')
    rname_lower = rname.lower()
    # Skip @everyone and bot-managed roles
    if rname_lower == '@everyone' or r.get('managed'):
        continue
    for check in game_names:
        if check in rname_lower or rname_lower in check:
            if r['id'] not in seen_role_ids:
                matched_roles.append({
                    'id': r['id'],
                    'name': rname,
                    'mentionable': r.get('mentionable', False)
                })
                seen_role_ids.add(r['id'])
            break

# Build result
result = {
    'search': search,
    'matched_games': [
        {'id': g.get('id'), 'name': g.get('name') or g.get('title')}
        for g in matched_games
    ],
    'matched_roles': matched_roles,
    'get_roles_channel': channel_url,
    'message': ''
}

if matched_roles:
    role_names = ', '.join('**' + r['name'] + '**' for r in matched_roles)
    result['message'] = (
        f'To access the game channel, you need the {role_names} role. '
        f'Head over to <#{channel_id}> and grab it!'
    )
elif matched_games:
    game_names_str = ', '.join(
        g.get('name') or g.get('title') for g in matched_games
    )
    result['message'] = (
        f'Found game(s): {game_names_str}, but I could not find an exact matching role. '
        f'Check <#{channel_id}> to see all available game roles.'
    )
else:
    result['message'] = (
        f'No game found matching \"{search}\". '
        f'Check <#{channel_id}> to browse all available game roles.'
    )

print(json.dumps(result, indent=2))
"

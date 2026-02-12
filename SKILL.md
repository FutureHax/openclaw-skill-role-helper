---
name: role-helper
description: Look up the Discord role needed for a game and direct players to #get-roles-here to self-assign the role.
metadata: {"openclaw":{"requires":{"env":["ZORDON_API_URL","ZORDON_API_KEY","DISCORD_BOT_TOKEN"]}}}
---

# Role Helper

Look up which Discord role a player needs to access a game channel, and direct them to the self-assignment channel if they don't have it.

## When to use this skill

Use this skill when:

- A player says they **can't access** a game channel or can't see it
- A player asks **how to join** a specific game or get access
- A player asks **what role** they need for a game
- A player mentions they're **missing permissions** or can't post in a game channel
- A player is new and asking how to get started with a specific game

## How to use

Run the lookup tool via exec:

```bash
bash {baseDir}/tools/lookup.sh <game_name_or_search>
```

### Examples

```bash
# Look up role for a game by name
bash {baseDir}/tools/lookup.sh "Curse of Strahd"

# Partial match works too
bash {baseDir}/tools/lookup.sh strahd

# Search by system or keyword
bash {baseDir}/tools/lookup.sh "pathfinder"
```

## Output format

Returns JSON with:

```json
{
  "search": "strahd",
  "matched_games": [
    {"id": 42, "name": "Curse of Strahd"}
  ],
  "matched_roles": [
    {"id": "123456789", "name": "Curse of Strahd", "mentionable": true}
  ],
  "get_roles_channel": "https://discord.com/channels/1296607220221345835/1383948225710522378",
  "message": "To access the game channel, you need the **Curse of Strahd** role. Head over to <#1383948225710522378> and grab it!"
}
```

## How to respond

1. Run the lookup tool with the game name the player mentioned
2. Use the `message` field from the response as the basis of your reply
3. If `matched_roles` is empty but `matched_games` has results, the game exists but the role name may differ — still direct them to <#1383948225710522378>
4. If nothing matches, let the player know and suggest they check <#1383948225710522378> to browse all available game roles

## Formatting for Discord

- Use the pre-formatted `message` from the JSON response — it already uses Discord channel mention syntax (`<#1383948225710522378>`)
- Bold the role name so it stands out
- Keep the response friendly and concise (1-3 lines)
- If multiple roles match, list them all

## Guidelines

- This is a **read-only** helper — it does NOT assign roles, only tells players where to get them
- The self-assignment channel is always <#1383948225710522378> (#get-roles-here)
- If a player seems confused about the process, explain: go to the channel, find the game role, and click/react to assign it to yourself

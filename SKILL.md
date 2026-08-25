---
name: role-helper
description: Help Discord users look up, add, and remove curated game-access roles (same allowlist as /get-roles). Use when someone cannot see a game channel, asks for a game role, wants to drop a game role, or asks what game roles they have. Never manages staff, color, mute, boost, or other non-game roles.
metadata: {"openclaw":{"requires":{"env":["DISCORD_BOT_TOKEN"]}}}
---

# Role Helper (game-access only)

Conversational self-serve for **curated game-access roles** only. The same role IDs as Zordon `/get-roles` / `ROLE_MENU_CATALOG`. The tool hard-refuses anything else before calling Discord.

## Red lines (mandatory)

1. **Game-access catalog only.** Never add/remove staff, admin, moderator, color, nitro/boost, mute, `@everyone`, bot-managed, or any role not returned by `catalog` / `lookup`.
2. **Never use `discord-manage` `role-add` / `role-remove` for players.** That skill is owner-only and can touch any role.
3. **Only the talking user.** Always pass their Discord user ID as `caller_discord_id`. Never change someone else's roles.
4. **Do not invent role IDs.** Only use IDs from this skill's tools.
5. If they ask for a non-game role: refuse briefly ("that is not a self-serve game role") and point them at `/get-roles` for game roles. Do not name or hint at privileged roles.
6. **You CAN flip game roles from chat.** When they name a game and want access, run `roles.sh add` (after unique `lookup`). Do **not** say you cannot flip it. Do **not** send them to `#get-roles-here`. Prefer `/get-roles` only for browsing many roles.

## When to use

- Cannot see / access a game channel
- "Give me Tomb of Annihilation" / "add Pirate Borg"
- "Drop / remove my Ten Candles role"
- "What game roles do I have?"
- "How do I get roles?" (prefer pointing at `/get-roles`; use this skill if they name a game)

## Tools

Paths are absolute on the OpenClaw host. Scripts load `~/.openclaw/.env` when present.

```bash
bash /home/marvin/.openclaw/workspaces/zordon/skills/role-helper/tools/roles.sh <action> [args...]
```

If the workspace copy is missing, the shared path is:

```bash
bash /home/marvin/.openclaw/skills/role-helper/tools/roles.sh <action> [args...]
```

### `catalog` — list allowlisted game roles

```bash
bash /home/marvin/.openclaw/workspaces/zordon/skills/role-helper/tools/roles.sh catalog
```

### `lookup <query>` — match catalog labels only

```bash
bash /home/marvin/.openclaw/workspaces/zordon/skills/role-helper/tools/roles.sh lookup "Tomb of Annihilation"
bash /home/marvin/.openclaw/workspaces/zordon/skills/role-helper/tools/roles.sh lookup tomb
```

Returns JSON. Use `message` when present. If `ambiguous match`, ask which label. Never treat a non-match as permission to call Discord yourself.

Legacy wrapper (same catalog-only behavior):

```bash
bash /home/marvin/.openclaw/workspaces/zordon/skills/role-helper/tools/lookup.sh "strahd"
```

### `status <caller_discord_id>` — their game roles only

```bash
bash /home/marvin/.openclaw/workspaces/zordon/skills/role-helper/tools/roles.sh status <caller_discord_id>
```

Returns only catalog roles the member already has (other guild roles are hidden on purpose).

### `add` / `remove` — self-serve write (gated)

```bash
bash /home/marvin/.openclaw/workspaces/zordon/skills/role-helper/tools/roles.sh add <caller_discord_id> "Pirate Borg"
bash /home/marvin/.openclaw/workspaces/zordon/skills/role-helper/tools/roles.sh remove <caller_discord_id> "Pirate Borg"
```

You may pass a catalog `roleId` snowflake instead of a label. Non-catalog snowflakes are refused with no Discord write.

**Confirm:** if `lookup` returns a unique match, you may `add`/`remove`. If ambiguous, list options and wait. Do not dump the full catalog unless they ask to browse (prefer `/get-roles` for browsing).

## How to respond

1. Resolve the inbound Discord user ID; that is always `caller_discord_id`.
2. For named games they want to play: `lookup`, then **immediately** `add` when the match is unique (they already asked for the change). Do not stop after naming the role.
3. Prefer the tool `message` field; keep replies to 1-3 friendly lines.
4. Point at `/get-roles` for browsing or multi-role menus. Never direct people to `#get-roles-here` for self-serve.
5. After a successful `add`, you may optionally use the `zordon-api` skill (`/games/schedule?days=7` and `/channels`) to mention upcoming games that match the new role. If lookup fails, omit games (do not say you could not look them up).
6. Discord `50013` / Missing Permissions: say Zordon cannot assign that game role until the bot role is above it in Server Settings; still name the game role they asked for.
7. Catalog labels are the source of truth (e.g. **Dragon Delves**). Do not invent alternate Discord role names like "Dragon Slayers".

## Catalog sync

`catalog.json` is copied from Zordon `src/data/roleMenus.js`. When Zordon's menu catalog changes, regenerate:

```bash
bash tools/regen-catalog.sh /path/to/zordon/src/data/roleMenus.js
```

Then redeploy this skill to the Zordon workspace.

## Env

- `DISCORD_BOT_TOKEN` (required for `status` / `add` / `remove`)
- Optional: `DISCORD_GUILD_ID` (defaults from OpenClaw config, else FutureHax guild)
- Optional for post-grant schedule hints: `ZORDON_API_URL`, `ZORDON_API_KEY` via `zordon-api`

# openclaw-skill-role-helper

OpenClaw skill for Zordon: look up, add, and remove **curated game-access Discord roles** only (same allowlist as Zordon `/get-roles`).

Staff, color, mute, boost, and every other guild role are unreachable. The tool enforces the allowlist before any Discord write.

Closes conversational gaps for "I can't see the channel" / "give me Tomb of Annihilation" without using owner-only `discord-manage`.

## Installation (Zordon only)

```bash
# Preferred: per-agent workspace
scp -r . openclaw:~/.openclaw/workspaces/zordon/skills/role-helper

# Do not install to shared ~/.openclaw/skills/ unless every agent should have it
```

Restart the gateway after installing:

```bash
ssh openclaw 'openclaw gateway restart'
```

## Contents

```
role-helper/
├── SKILL.md              # Agent instructions
├── README.md
├── catalog.json          # Allowlisted game-access roles (from Zordon)
├── lib/                  # Catalog load, resolve, gates
├── tests/                # Offline allowlist tests
└── tools/
    ├── roles.sh          # catalog | status | lookup | add | remove
    ├── lookup.sh         # thin wrapper → roles.sh lookup
    └── regen-catalog.sh  # refresh catalog.json from Zordon roleMenus.js
```

## Regenerate catalog

When Zordon's `ROLE_MENU_CATALOG` changes:

```bash
bash tools/regen-catalog.sh /path/to/zordon/src/data/roleMenus.js
```

## Tests

```bash
python3 tests/test_gates.py -v
```

## License

MIT

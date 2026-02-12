# openclaw-skill-role-helper

An [OpenClaw](https://clawd.bot) agent skill: Look up the Discord role needed for a game and direct players to #get-roles-here to self-assign.

## Installation

Copy the skill to the OpenClaw skills directory:

```bash
# Shared (all agents)
scp -r role-helper your-vps:~/.openclaw/skills/role-helper

# Per-agent
scp -r role-helper your-vps:~/.openclaw/workspaces/<agent>/skills/role-helper
```

Restart the gateway after installing:

```bash
openclaw gateway restart
```

## Skill contents

```
role-helper/
├── SKILL.md           # Skill definition and agent instructions
├── README.md          # This file
└── tools/             # Implementation scripts
    └── lookup.sh      # Game-to-role lookup tool
```

## License

MIT

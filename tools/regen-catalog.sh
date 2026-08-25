#!/usr/bin/env bash
# Regenerate catalog.json from Zordon's ROLE_MENU_CATALOG.
# Usage: bash tools/regen-catalog.sh /path/to/zordon/src/data/roleMenus.js
set -euo pipefail

SOURCE="${1:?Usage: regen-catalog.sh /path/to/zordon/src/data/roleMenus.js}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/catalog.json"

if [[ ! -f "$SOURCE" ]]; then
  echo "{\"error\":\"source not found\",\"path\":\"${SOURCE}\"}" >&2
  exit 1
fi

SOURCE_ABS="$(cd "$(dirname "$SOURCE")" && pwd)/$(basename "$SOURCE")"
node --input-type=module <<EOF
import { writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const mod = await import(pathToFileURL("${SOURCE_ABS}").href);
const catalog = mod.ROLE_MENU_CATALOG;
if (!Array.isArray(catalog) || catalog.length === 0) {
  console.error(JSON.stringify({ error: "ROLE_MENU_CATALOG missing or empty" }));
  process.exit(1);
}

const categories = catalog.map((category) => ({
  id: category.id,
  label: category.label,
  roles: (category.roles || []).map((role) => ({
    roleId: role.roleId,
    label: role.label,
    generalChannelId: role.generalChannelId || "",
  })),
}));

const payload = {
  source: "zordon ROLE_MENU_CATALOG (src/data/roleMenus.js)",
  updatedNote: "Regenerate with: bash tools/regen-catalog.sh /path/to/zordon/src/data/roleMenus.js",
  categories,
};

writeFileSync("${OUT}", JSON.stringify(payload, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ ok: true, path: "${OUT}", roleCount: categories.reduce((n, c) => n + c.roles.length, 0) }));
EOF

/**
 * /usr/bin/env node
 * Generates shared/styles/tokens.css from shared/styles/tokens.json (ADR-004 / PFX-06).
 * Run: node scripts/generate-css-tokens.mjs
 * Re-run any time tokens.json changes — tokens.css is a build artifact, not hand-edited.
 */

import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const tokensPath = path.resolve(__dirname, '../src/shared/styles/tokens.json')
const outPath = path.resolve(__dirname, '../src/shared/styles/tokens.css')

const tokens = JSON.parse(readFileSync(tokensPath, 'utf-8'))

/** camelCase -> kebab-case for CSS custom property segments. */
function kebab(s) {
  return s.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()
}

const lines = []

function walk(node, pathSegments) {
  if (node === null || typeof node !== 'object') {
    lines.push(`  --${pathSegments.map(kebab).join('-')}: ${node};`)
    return
  }
  for (const [key, value] of Object.entries(node)) {
    if (key.startsWith('_') || key.startsWith('$')) continue // skip _note / $schema annotations
    walk(value, [...pathSegments, key])
  }
}

walk(tokens, [])

const output = `/**
 * GENERATED FILE — do not hand-edit. Source: shared/styles/tokens.json (ADR-004).
 * Regenerate with: node scripts/generate-css-tokens.mjs
 */

:root {
${lines.join('\n')}
}
`

writeFileSync(outPath, output)
console.log(`Wrote ${lines.length} custom properties to ${path.relative(process.cwd(), outPath)}`)

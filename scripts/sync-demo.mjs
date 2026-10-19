import { access, mkdir, copyFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const target = fileURLToPath(new URL('../web/public/demo/', import.meta.url))
await mkdir(target, { recursive: true })
let source = '../artifacts/releases/'
try { await access(new URL(`${source}decisions.jsonl`, import.meta.url)) } catch { source = '../artifacts/demo/' }
for (const name of ['decisions.jsonl', 'decisions.manifest.json', 'evaluation.json']) {
  await copyFile(new URL(`${source}${name}`, import.meta.url), `${target}/${name}`)
}
await copyFile(new URL(`${source}${source.includes('releases') ? 'dqn/training.json' : 'q-agent.training.json'}`, import.meta.url), `${target}/training.json`)

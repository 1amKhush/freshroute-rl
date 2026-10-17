import { mkdir, copyFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const target = fileURLToPath(new URL('../web/public/demo/', import.meta.url))
await mkdir(target, { recursive: true })
for (const name of ['decisions.jsonl', 'decisions.manifest.json', 'evaluation.json', 'q-agent.training.json']) {
  await copyFile(new URL(`../artifacts/demo/${name}`, import.meta.url), `${target}/${name}`)
}

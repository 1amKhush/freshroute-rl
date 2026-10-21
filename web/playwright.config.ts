import { defineConfig } from '@playwright/test'
import { existsSync } from 'node:fs'
export default defineConfig({
  testDir: './e2e', workers: 1, use: {
    baseURL: process.env.LAB_URL || 'http://127.0.0.1:5173',
    launchOptions: { executablePath: process.env.CHROME_PATH || (existsSync('/usr/bin/google-chrome') ? '/usr/bin/google-chrome' : undefined), args: ['--no-sandbox'] },
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { resolve } from 'path'

const mpaPages = [
  'dashboard', 'monitoring', 'tenders', 'knowledge', 'settings',
  'ppr2025', 'learning', 'pricing', 'clauses', 'trust-chat',
]

const rollupInput: Record<string, string> = {
  main: resolve(__dirname, 'index.html'),
}
for (const p of mpaPages) {
  rollupInput[p] = resolve(__dirname, `mpa/${p}.html`)
}

export default defineConfig({
  plugins: [react()],
  // D: is space-constrained; keep Vite's dep-optimizer cache on C: (mirrors frontend/'s setup)
  cacheDir: 'C:/Users/znasi/.vite-cache/procureflow-frontend-v2',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@app': path.resolve(__dirname, './src/app'),
      '@features': path.resolve(__dirname, './src/features'),
      '@entities': path.resolve(__dirname, './src/entities'),
      '@widgets': path.resolve(__dirname, './src/widgets'),
      '@shared': path.resolve(__dirname, './src/shared'),
      '@layouts': path.resolve(__dirname, './src/layouts'),
      '@providers': path.resolve(__dirname, './src/providers'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5175,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  base: './',
  build: {
    outDir: 'dist',
    rollupOptions: { input: rollupInput },
  },
})

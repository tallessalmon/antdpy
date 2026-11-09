import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: '../src/antdpy/static',
    emptyOutDir: true,
    chunkSizeWarningLimit: 4000,
  },
  server: {
    // dev: `npm run dev` + `python examples/demo.py` (porta 8000)
    proxy: { '/_antdpy': { target: 'ws://127.0.0.1:8000', ws: true } },
  },
  test: { environment: 'jsdom', setupFiles: ['./src/test-setup.js'] },
})

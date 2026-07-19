import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

// The app is built as ONE self-contained index.html (scripts, styles, and
// fonts all inlined). That lets the exact same build work both ways:
//  - served by `scrapbook serve` at localhost:8420
//  - opened straight from a folder/USB stick via file:// (the static-book
//    export), where browsers refuse to load external module scripts.
export default defineConfig({
  base: './',
  plugins: [react(), viteSingleFile()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8420',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})

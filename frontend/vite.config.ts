import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // ПРОБЛЕМА: GitHub Pages размещает сайт по /REA_auction/; без base не грузятся JS/CSS.
  // РЕШЕНИЕ: для Pages используем префикс репозитория, локально оставляем '/'.
  base: process.env.GITHUB_PAGES === 'true' ? '/REA_auction/' : '/',
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})

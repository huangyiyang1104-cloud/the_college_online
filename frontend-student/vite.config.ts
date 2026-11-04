import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 学员端独立工程：生产部署在 /，开发端口 5173
export default defineConfig({
  base: '/',
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 管理端独立工程：生产部署在 /admin，开发端口 5174
export default defineConfig({
  base: '/admin/',
  plugins: [vue()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})

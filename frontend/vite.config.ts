import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0', // Bind to all interfaces for dev container access
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8500',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8500',
        ws: true,
      },
      '/charts': {
        target: 'http://localhost:8500',
        changeOrigin: true,
      },
    },
  },
})

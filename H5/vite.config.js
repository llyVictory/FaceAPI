import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import basicSsl from '@vitejs/plugin-basic-ssl'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    basicSsl()
  ],
  server: {
    host: true, // Expose to Network
    https: true, // Enable HTTPS for camera access
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://172.26.70.234:8070',
        changeOrigin: true,
        secure: false, // Target is HTTP, so no need to verify SSL
      }
    }
  }
})

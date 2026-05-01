import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],

  server: {
    proxy: {
      '/login': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/register': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/logout': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/chat': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
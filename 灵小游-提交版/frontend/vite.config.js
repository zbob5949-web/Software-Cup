import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/sessions': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/digital-human-3d': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/live2d': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/Resources': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
        },
    },
});

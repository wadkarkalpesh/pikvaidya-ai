import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'robots.txt', '*.wasm'],
      manifest: {
        name: 'PikVaidya AI — Agricultural Diagnostic Platform',
        short_name: 'PikVaidya',
        description: 'AI-powered crop pathology diagnosis, Grad-CAM visual explainability, and context-aware farming advisory.',
        theme_color: '#15803d',
        background_color: '#f8fafc',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        maximumFileSizeToCacheInBytes: 35 * 1024 * 1024, // 35 MB to support ONNX models and WASM binaries
        globPatterns: ['**/*.{js,css,html,ico,png,svg,webp,wasm}'],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/models/') || url.pathname.endsWith('.wasm') || url.pathname.endsWith('.onnx'),
            handler: 'CacheFirst',
            options: {
              cacheName: 'pikvaidya-models-wasm-cache',
              expiration: {
                maxEntries: 25,
                maxAgeSeconds: 60 * 60 * 24 * 60, // 60 days
              },
            },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/v1/diseases'),
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'agricultural-knowledge-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 60 * 24 * 7, // 7 days
              },
            },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/v1/assistant/chunks'),
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'assistant-chunks-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 14, // 14 days
              },
            },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/v1/weather/locations'),
            handler: 'CacheFirst',
            options: {
              cacheName: 'weather-locations-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
              },
            },
          },
        ],
      },
    }),
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/models': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});

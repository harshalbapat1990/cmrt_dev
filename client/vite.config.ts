import path from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // `mode` is injected by Vite ("development" | "production") -- always reliable
  const env = loadEnv(mode, process.cwd(), 'VITE_')

  return {
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },

    // Useful for local dev over LAN/Container dev
    server: {
      host: true,
      port: 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_URL,
          changeOrigin: true,
        },
      },
    },

    // process.env.VITE_* is set by Docker ARG/ENV and takes precedence over .env files here
    define: {
      'import.meta.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || env.VITE_API_URL || ''),
    },

    plugins: [
      react({
        babel: {
          plugins: ['babel-plugin-react-compiler'],
        },
      }),
      tailwindcss(),
    ],

    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            'vendor-mui':   ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
            'vendor-xlsx':  ['xlsx'],
          },
        },
      },
    },

    // Controls `vite preview` (what you're running in the container)
    preview: {
      host: true,
      port: 5173,
      strictPort: true,
      allowedHosts: [
        'cmrt-frontend-app.thankfuldune-b5b5a5d0.australiaeast.azurecontainerapps.io',
        'cmrt-frontend-app-dev.graysky-b0f7ba4d.australiaeast.azurecontainerapps.io',
        'cmrt-frontend-app-dev--v2.graysky-b0f7ba4d.australiaeast.azurecontainerapps.io',
        'cmrt-frontend-app-dev--v3.graysky-b0f7ba4d.australiaeast.azurecontainerapps.io',
        'cmrt-frontendapp-prod-ae-001.gentlebush-7786ab03.australiaeast.azurecontainerapps.io',
        'cmrt-frontend-prod-ae-001.politefield-870deeaf.australiaeast.azurecontainerapps.io'
      ],
    },
  }
})

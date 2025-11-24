import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { createProxyMiddleware } from 'http-proxy-middleware'

const backendUrl = process.env.VITE_API_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [svelte()],
  server: {
    middlewares: [
      {
        name: 'raw-proxy',
        apply: 'pre',
        async handle(req, res, next) {
          const url = req.url?.split('?')[0] || '/'

          // Proxy /{relic_id}/raw requests to backend BEFORE other middleware
          if (url.match(/^\/[a-zA-Z0-9_-]+\/raw$/)) {
            const middleware = createProxyMiddleware({
              target: backendUrl,
              changeOrigin: true
            })
            return middleware(req, res, next)
          }

          next()
        }
      }
    ],
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api')
      }
    }
  }
})

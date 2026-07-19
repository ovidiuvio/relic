import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { createProxyMiddleware } from 'http-proxy-middleware'

const backendUrl = process.env.VITE_API_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [svelte()],
  define: {
    'process.env': {}
  },
  optimizeDeps: {
    // monaco-editor is imported only dynamically (MonacoEditor.svelte), and Vite's
    // startup scanner does not discover it. Without this it gets optimized on demand
    // the first time an editor opens, which costs a ~20s prebundle of its 961 ESM
    // modules AND a forced full page reload ("optimized dependencies changed").
    // The dev container keeps node_modules in an anonymous volume, so that recurs
    // after every dev-down/dev-up. Listing it here prebundles it at server start.
    include: ['pdfjs-dist', 'monaco-editor']
  },
  // No manualChunks here, deliberately. Vite 8 is rolldown-based, where
  // rollupOptions.output.manualChunks is a compat path: with rules for
  // monaco/pdfjs/highlight, rolldown placed the shared __vitePreload helper inside
  // the monaco chunk. The entry needs that helper for every lazy route import, so it
  // gained a static edge to the monaco chunk and Vite modulepreloaded all 3.7 MB of
  // it on first paint (initial payload 4,010 kB vs 234 kB without). The dynamic
  // import()s in routes.js and the processors already split these out on their own.
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

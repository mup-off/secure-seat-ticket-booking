import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In development the React app runs on http://localhost:5173 and forwards /api to
// Django on port 8000. The browser sees one origin, so the session and CSRF cookies
// work without opening up CORS. In production Django serves the built files itself.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
  build: {
    sourcemap: false, // don't publish source maps in production
  },
});

import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backend = env.MATHS_BACKEND_URL || 'http://127.0.0.1:8005';
  return {
    plugins: [react()],
    base: '/chat/',
    build: {
      outDir: '../agent_platform/static/chat', emptyOutDir: true,
      rollupOptions: { output: { manualChunks: { math: ['katex', 'rehype-katex'] } } },
    },
    server: {
      strictPort: true,
      proxy: Object.fromEntries(['/v1', '/health', '/trace-viewer', '/docs', '/openapi.json']
        .map(path => [path, { target: backend, changeOrigin: true }])),
    },
  };
});

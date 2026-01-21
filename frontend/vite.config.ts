import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      imports: ['vue', 'vue-router', 'pinia'],
      resolvers: [ElementPlusResolver()],
      dts: 'src/auto-imports.d.ts',
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@core': resolve(__dirname, 'src/core'),
      '@modules': resolve(__dirname, 'src/modules'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    strictPort: true,
    // Docker 环境下的 HMR 配置
    // 注意：在 Windows 本地开发时，host: '0.0.0.0' 可能会导致 WebSocket 连接失败从而不断刷新
    // 如果是在 Docker 中运行，请取消注释
    // hmr: {
    //   protocol: 'ws',
    //   host: '0.0.0.0',
    //   port: 5173,
    // },
    watch: {
      usePolling: true, // Docker 环境下启用轮询，确保文件更改被检测到
      interval: 1000,
    },
    // 添加缓存控制头，防止浏览器缓存 JS 文件
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
    },
    proxy: {
      '/api': {
        // 支持环境变量配置，默认使用 localhost（本地开发）
        // 在 Docker 环境中通过 VITE_API_TARGET 环境变量指定 backend 服务地址
        target: process.env.VITE_API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        // 启用 WebSocket 代理支持
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
        },
      },
    },
  },
})

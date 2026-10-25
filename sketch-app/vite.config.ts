import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Engineer Sketch —— 本地静态构建
// 产物经 `npm run deploy` 拷入 ../resources/sketch/，由 Engineer Desk 启动本地 HTTP 服务后
// 用系统浏览器打开。base 必须为 "./"，保证所有资源走相对路径。
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    assetsDir: "assets",
    // Excalidraw 体积较大（约 2MB），放宽告警阈值
    chunkSizeWarningLimit: 4000,
  },
});

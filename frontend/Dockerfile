# 前端生产环境 Dockerfile
# 多阶段构建：先构建 React 应用，再用 Node 运行带代理的静态文件服务

# 阶段 1: 构建
FROM node:20-alpine AS builder

WORKDIR /app

# 配置国内 npm 源
RUN npm config set registry https://registry.npmmirror.com

# 复制依赖文件
COPY package.json package-lock.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# 阶段 2: 运行（带 API 代理的静态服务器）
FROM node:20-alpine

WORKDIR /app

# 复制构建产物
COPY --from=builder /app/dist ./dist

# 创建 package.json 并本地安装代理依赖
RUN echo '{"name":"proxy-server","version":"1.0.0"}' > package.json && \
    npm config set registry https://registry.npmmirror.com && \
    npm install express http-proxy-middleware

# 创建代理服务器脚本
RUN echo 'const express = require("express"); \
const { createProxyMiddleware } = require("http-proxy-middleware"); \
const path = require("path"); \
const app = express(); \
app.use("/api", createProxyMiddleware({ target: "http://backend:8000/api", changeOrigin: true, ws: true })); \
app.use(express.static(path.join(__dirname, "dist"))); \
app.use((req, res) => res.sendFile(path.join(__dirname, "dist", "index.html"))); \
app.listen(80, "0.0.0.0", () => console.log("Server running on port 80"));' \
> server.cjs

# 暴露 80 端口
EXPOSE 80

# 启动服务器
CMD ["node", "server.cjs"]

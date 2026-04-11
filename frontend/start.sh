#!/bin/bash

echo "🚀 启动 Travel Hub 前端应用..."
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
  echo "❌ 未检测到 Node.js，请先安装 Node.js >= 18.0"
  exit 1
fi

echo "✅ Node.js 版本: $(node --version)"
echo "✅ npm 版本: $(npm --version)"
echo ""

# 检查依赖
if [ ! -d "node_modules" ]; then
  echo "📦 安装依赖中..."
  npm install
else
  echo "✅ 依赖已安装"
fi

echo ""
echo "🎯 启动开发服务器..."
echo "📍 访问地址: http://localhost:5173"
echo ""

npm run dev

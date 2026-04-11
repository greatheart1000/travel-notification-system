#!/usr/bin/env python3
"""
Travel Hub 开发环境启动脚本
同时启动后端服务和前端开发服务器
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def print_banner():
    print(
        """
    ╔════════════════════════════════════════════════════════════╗
    ║           🚀 Travel Hub 开发环境启动脚本 🚀               ║
    ║                 行程管家服务流程数字化                      ║
    ╚════════════════════════════════════════════════════════════╝
    """
    )


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def check_python():
    """检查 Python 版本"""
    print("✓ 检查 Python 环境...")
    print(f"✅ Python 版本: {sys.version.split()[0]}\n")


def check_node():
    """检查 Node.js"""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Node.js 版本: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        print("❌ 未找到 Node.js，请先安装 Node.js >= 18.0")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Node.js 版本检查超时，请确认 Node.js 安装是否正常")
        return False
    return False


def install_backend_deps():
    """安装后端依赖"""
    print_section("📦 安装后端依赖")

    # 检查 pyproject.toml
    if Path("pyproject.toml").exists():
        print("✓ 检测到 pyproject.toml")
        print("💡 使用建议:\n")
        print("  pip install -e .              # 开发模式安装")
        print("  或使用 Poetry: poetry install # 如果使用 Poetry")
    else:
        print("⚠️  未找到 pyproject.toml")


def setup_frontend():
    """设置前端环境"""
    print_section("🎨 设置前端环境")

    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ 未找到 frontend 目录")
        return False

    os.chdir(frontend_dir)

    # 检查 node_modules
    if not Path("node_modules").exists():
        print("📦 安装前端依赖...")
        result = subprocess.run(["npm", "install"], timeout=600)
        if result.returncode != 0:
            print("❌ 前端依赖安装失败")
            return False
    else:
        print("✅ 前端依赖已安装")

    os.chdir("..")
    return True


def print_startup_info():
    """打印启动信息"""
    print_section("🎯 服务启动信息")

    print(
        """
    后端 API 服务器:
    ├─ URL: http://localhost:8000
    ├─ 文档: http://localhost:8000/docs (如果使用 FastAPI)
    └─ 状态: 等待启动...

    前端开发服务器:
    ├─ URL: http://localhost:5173
    └─ 状态: 等待启动...

    🔗 访问地址: http://localhost:5173

    ✨ 开发工作流:
    1. 前端代码修改时自动刷新 (Hot Module Replacement)
    2. 后端代码修改需要重启服务
    3. API 请求自动代理到后端
    4. 使用浏览器开发者工具调试

    按 Ctrl+C 停止所有服务
    """
    )


def start_services():
    """启动所有服务"""
    print_section("🚀 启动服务")

    processes = []

    try:
        # 启动后端
        print("📤 启动后端服务...")
        print("💡 后端启动命令:")
        print("   cd src && uvicorn app.main:app --reload --port 8000")
        print("   或: python -m app.main")
        print("\n⚠️  请在另一个终端中手动启动后端服务\n")

        # 启动前端
        print("📱 启动前端开发服务...")
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd="frontend",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        processes.append(("前端", frontend_process))
        print("✅ 前端开发服务已启动\n")

        # 等待一下让服务完全启动
        time.sleep(3)

        print_startup_info()

        # 保持运行
        print("\n⏳ 服务运行中... (按 Ctrl+C 退出)\n")
        for name, proc in processes:
            proc.wait()

    except KeyboardInterrupt:
        print("\n\n⏹️  收到中断信号，正在关闭服务...")
        for name, proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"✅ {name}服务已关闭")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"❌ {name}服务强制关闭")

        print("\n👋 再见！")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)


def main():
    print_banner()

    # 检查环境
    check_python()
    if not check_node():
        sys.exit(1)

    # 安装依赖
    install_backend_deps()
    if not setup_frontend():
        sys.exit(1)

    # 启动服务
    start_services()


if __name__ == "__main__":
    main()

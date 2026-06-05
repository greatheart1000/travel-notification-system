#!/bin/bash
# ============================================================
# 阿里云 FC 代码包构建脚本
# ============================================================
# 用法:
#   bash deploy/fc/package.sh          # 构建后端 zip
#   bash deploy/fc/package.sh --image  # 构建 Docker 镜像
#   bash deploy/fc/package.sh --all    # 构建全部
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$REPO_ROOT/deploy/fc/build"
ZIP_OUTPUT="$REPO_ROOT/deploy/fc/travel-notification-fc.zip"
IMAGE_NAME="${IMAGE_NAME:-travel-notification-fc:latest}"

log()  { echo "[package] $*"; }
die()  { echo "[package] ERROR: $*" >&2; exit 1; }

# ────────────────────────────────────────────
# 方式 A：ZIP 包部署（代码包方式上传到 FC）
# ────────────────────────────────────────────
build_zip() {
    log "清理构建目录..."
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"

    # 1. 安装 Python 依赖到构建目录
    log "安装 Python 依赖..."
    pip install \
        --target="$BUILD_DIR" \
        --platform manylinux2014_x86_64 \
        --python-version 3.10 \
        --only-binary=:all: \
        fastapi \
        uvicorn \
        pydantic \
        pydantic-core \
        pymysql \
        python-multipart \
        apscheduler \
        starlette \
        httpx \
        jinja2 \
        anyio \
        typing-extensions \
        annotated-types \
        annotated-doc \
        tzlocal \
        certifi \
        httpcore \
        h11 \
        click \
        idna \
        sniffio \
        MarkupSafe \
        2>&1

    # 2. 安装项目本身（editable 模式不行，直接复制代码）
    log "复制项目源码..."
    mkdir -p "$BUILD_DIR/app"
    cp -r "$REPO_ROOT/src/app" "$BUILD_DIR/app"
    # 确保包级别的 __init__.py
    touch "$BUILD_DIR/app/__init__.py"

    # 3. 复制 bootstrap
    cp "$SCRIPT_DIR/bootstrap" "$BUILD_DIR/"
    chmod +x "$BUILD_DIR/bootstrap"

    # 4. 创建 travel_notification_system 包标记
    mkdir -p "$BUILD_DIR/travel_notification_system.egg-info"
    cat > "$BUILD_DIR/travel_notification_system.egg-info/PKG-INFO" <<'EOF'
Metadata-Version: 2.1
Name: travel-notification-system
Version: 0.1.0
EOF

    # 5. 打包为 zip
    log "打包为 zip..."
    cd "$BUILD_DIR" && zip -r "$ZIP_OUTPUT" . -x "*.pyc" -x "__pycache__/*"

    log "构建完成: $ZIP_OUTPUT ($(du -h "$ZIP_OUTPUT" | cut -f1))"

    # 6. 验证 zip 内容
    log "zip 内容预览（前 30 个文件）:"
    unzip -l "$ZIP_OUTPUT" | head -35
}

# ────────────────────────────────────────────
# 方式 B：容器镜像部署
# ────────────────────────────────────────────
build_image() {
    log "构建 Docker 镜像: $IMAGE_NAME"
    docker build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Dockerfile" "$REPO_ROOT"

    log "镜像构建完成: $IMAGE_NAME"
    docker images "$IMAGE_NAME"
}

# ────────────────────────────────────────────
# 方式 C：构建前端（部署到 OSS）
# ────────────────────────────────────────────
build_frontend() {
    log "构建前端..."
    cd "$REPO_ROOT/frontend" && npm run build

    FRONTEND_DIST="$REPO_ROOT/frontend/dist"
    FRONTEND_ZIP="$REPO_ROOT/deploy/fc/frontend-oss.zip"

    # 创建前端部署包（可直接上传到 OSS）
    cd "$FRONTEND_DIST" && zip -r "$FRONTEND_ZIP" .

    log "前端构建完成: $FRONTEND_ZIP ($(du -h "$FRONTEND_ZIP" | cut -f1))"
    log ""
    log "前端部署步骤:"
    log "  1. 在阿里云 OSS 创建 Bucket（公共读）"
    log "  2. 上传 $FRONTEND_ZIP 到 OSS 并解压"
    log "  3. 配置静态网站托管，索引页: index.html"
    log "  4. 配置 CDN 加速（可选）"
    log ""
    log "  重要：需要在前端代码中将 API_BASE_URL 改为 FC 函数的公网地址"
    log "  修改 frontend/src 中的 API base URL 后重新 build"
}

# ────────────────────────────────────────────
check_prereqs() {
    command -v python3 >/dev/null 2>&1 || die "需要 python3"
    command -v zip >/dev/null 2>&1 || die "需要 zip"
    command -v npm >/dev/null 2>&1 || die "需要 npm (用于前端构建)"
}

# ────────────────────────────────────────────
main() {
    check_prereqs

    case "${1:-zip}" in
        zip)
            build_zip
            ;;
        image|docker)
            command -v docker >/dev/null 2>&1 || die "需要 Docker"
            build_image
            ;;
        frontend)
            build_frontend
            ;;
        all)
            build_zip
            build_frontend
            ;;
        *)
            echo "Usage: $0 {zip|image|frontend|all}"
            exit 1
            ;;
    esac

    log "完成！"
    log ""
    log "=== FC 部署步骤 ==="
    log "方法1 - 代码包:"
    log "  1. 打开 FC 控制台 -> 创建函数"
    log "  2. 运行时: 自定义运行时 (custom)"
    log "  3. 上传 $ZIP_OUTPUT"
    log "  4. 设置环境变量（见下方）"
    log "  5. 创建 HTTP 触发器"
    log ""
    log "方法2 - 容器镜像:"
    log "  1. 推送镜像到 ACR"
    log "  2. FC 选择容器镜像部署"
    log ""
    log "=== 环境变量配置 ==="
    log "  TRAVEL_NOTIFICATION_PERSISTENCE_BACKEND=json"
    log "  TRAVEL_NOTIFICATION_CORS_ORIGINS=<前端域名>"
    log ""
    log "=== 前端 ==="
    log "  将 frontend/dist 上传到 OSS，配置静态网站托管"
    log "  API 地址指向 FC 函数的公网 URL"
    log "  参考: https://help.aliyun.com/zh/fc/"
}

main "${@}"

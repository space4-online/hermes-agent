#!/usr/bin/env bash
# ============================================================================
# Hermes Agent 宿主机依赖安装脚本（Ubuntu 22.04 LTS）
#
# 一次性在新机器上执行，准备好运行 hermes-agent docker 部署所需的全部依赖。
# 脚本会创建专用部署用户（默认 server），所有数据/凭证都放在其家目录下。
#
# 使用（带 sudo 权限的初始用户，如 ubuntu / root 均可）：
#   wget -O setup-host-ubuntu22.sh <raw-url>
#   chmod +x setup-host-ubuntu22.sh
#   ./setup-host-ubuntu22.sh                  # 默认部署用户 server
#   DEPLOY_USER=foo ./setup-host-ubuntu22.sh  # 自定义部署用户
#
# 完成后即可：
#   1. 在 GitHub repo settings → environments → hermes-product 配置 vars/secrets
#   2. push 到 master 自动触发 .github/workflows/build-deploy-server.yml
# ============================================================================
set -euo pipefail

# ---------- 配置（可通过环境变量覆盖）----------
DEPLOY_USER="${DEPLOY_USER:-server}"
DEPLOY_USER_HOME="/home/${DEPLOY_USER}"
HERMES_DATA_DIR="${HERMES_DATA_DIR:-${DEPLOY_USER_HOME}/.hermes}"
HERMES_ENV_DIR="${HERMES_ENV_DIR:-${DEPLOY_USER_HOME}/env}"
HERMES_PORT="${HERMES_PORT:-8642}"
MYSQL_DATA_DIR="${MYSQL_DATA_DIR:-/data/hermes-mysql}"
SWAP_SIZE_GB="${SWAP_SIZE_GB:-4}"           # 0 表示不创建 swap

# ---------- 国内镜像加速 / ACR 配置 ----------
# CN_MIRROR=1（默认）则全面启用：apt 源 + Docker CE 源 + daemon.json 镜像加速
CN_MIRROR="${CN_MIRROR:-1}"
APT_MIRROR_HOST="${APT_MIRROR_HOST:-mirrors.aliyun.com}"
ACR_REGISTRY="${ACR_REGISTRY:-crpi-vz0a3h0d9w77e3sp.cn-shanghai.personal.cr.aliyuncs.com}"
ACR_NAMESPACE="${ACR_NAMESPACE:-my_workflow}"
# !!! 安全警告：以下 ACR 凭证已硬编码到脚本，请勿将仓库设为 public、切勿 fork/复制出去
ACR_USERNAME="${ACR_USERNAME:-baiyan138919}"
ACR_PASSWORD="${ACR_PASSWORD:-51JDK@520}"

# ---------- HTTPS 反代（如传入域名则启用 Nginx + certbot）----------
HERMES_DOMAIN="${HERMES_DOMAIN:-agent-h.codeshark.cn}"  # 默认响应域名；需预先 DNS 解析到本机公网 IP
CERTBOT_EMAIL="${CERTBOT_EMAIL:-admin@codeshark.cn}"   # Let's Encrypt 联系邮箱
if [ -n "$HERMES_DOMAIN" ]; then
  ENABLE_HTTPS=1
  [ -z "$CERTBOT_EMAIL" ] && CERTBOT_EMAIL="admin@${HERMES_DOMAIN#*.}"
else
  ENABLE_HTTPS=0
fi

log() { printf '\033[1;32m[setup]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[err]\033[0m %s\n' "$*" >&2; }

# 允许 root 或普通用户 +sudo 执行
if [ "$(id -u)" -ne 0 ] && ! sudo -n true 2>/dev/null && ! sudo -v 2>/dev/null; then
  err "需要 sudo 权限执行本脚本。"
  exit 1
fi

# ---------- 1. 系统更新 + 基础包 ----------
if [ "$CN_MIRROR" = "1" ]; then
  log "切换 apt 源到国内镜像 $APT_MIRROR_HOST"
  if [ -f /etc/apt/sources.list ] && ! grep -q "$APT_MIRROR_HOST" /etc/apt/sources.list 2>/dev/null; then
    sudo cp -n /etc/apt/sources.list /etc/apt/sources.list.bak || true
    sudo sed -i \
      -e "s|http://archive.ubuntu.com|https://${APT_MIRROR_HOST}|g" \
      -e "s|http://security.ubuntu.com|https://${APT_MIRROR_HOST}|g" \
      -e "s|http://cn.archive.ubuntu.com|https://${APT_MIRROR_HOST}|g" \
      /etc/apt/sources.list
  fi
  # Ubuntu 24+ 使用 DEB822
  if [ -f /etc/apt/sources.list.d/ubuntu.sources ] && ! grep -q "$APT_MIRROR_HOST" /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null; then
    sudo cp -n /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak || true
    sudo sed -i \
      -e "s|http://archive.ubuntu.com|https://${APT_MIRROR_HOST}|g" \
      -e "s|http://security.ubuntu.com|https://${APT_MIRROR_HOST}|g" \
      /etc/apt/sources.list.d/ubuntu.sources
  fi
fi

log "更新 apt 源并安装基础工具"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl gnupg lsb-release \
  vim git tmux htop jq ufw rsync unzip \
  build-essential

# ---------- 2. 时区 & NTP ----------
log "配置时区 Asia/Shanghai 并启用 NTP"
sudo timedatectl set-timezone Asia/Shanghai || true
sudo timedatectl set-ntp true || true

# ---------- 3. 安装 Docker CE + Compose v2 插件 ----------
if ! command -v docker >/dev/null 2>&1; then
  log "安装 Docker CE"
  sudo install -m 0755 -d /etc/apt/keyrings
  if [ "$CN_MIRROR" = "1" ]; then
    DOCKER_REPO_URL="https://${APT_MIRROR_HOST}/docker-ce/linux/ubuntu"
    DOCKER_GPG_URL="https://${APT_MIRROR_HOST}/docker-ce/linux/ubuntu/gpg"
    log "  使用国内 docker-ce 镜像: $DOCKER_REPO_URL"
  else
    DOCKER_REPO_URL="https://download.docker.com/linux/ubuntu"
    DOCKER_GPG_URL="https://download.docker.com/linux/ubuntu/gpg"
  fi
  curl -fsSL "$DOCKER_GPG_URL" \
    | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    $DOCKER_REPO_URL $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
                          docker-buildx-plugin docker-compose-plugin
else
  log "Docker 已安装，跳过 ($(docker --version))"
fi

# ---------- 4. 创建部署用户 ----------
if id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  log "部署用户 $DEPLOY_USER 已存在，跳过创建"
else
  log "创建部署用户 $DEPLOY_USER（仅 SSH 密钥登录，不设密码）"
  sudo useradd -m -s /bin/bash -c "hermes deployment" "$DEPLOY_USER"
  # 锁定密码登录，仅允许 SSH key 进来
  sudo passwd -l "$DEPLOY_USER" >/dev/null
fi

# 加入 sudo 组（运维便利，可选）与 docker 组（必须）
if ! id -nG "$DEPLOY_USER" | grep -qw sudo; then
  log "将 $DEPLOY_USER 加入 sudo 组"
  sudo usermod -aG sudo "$DEPLOY_USER"
fi
if ! id -nG "$DEPLOY_USER" | grep -qw docker; then
  log "将 $DEPLOY_USER 加入 docker 组"
  sudo usermod -aG docker "$DEPLOY_USER"
fi

# ---------- 5. 配置 Docker daemon（日志轮转 + 国内镜像加速）----------
log "配置 /etc/docker/daemon.json (log-rotate + 国内镜像加速)"
sudo mkdir -p /etc/docker
if [ ! -f /etc/docker/daemon.json ]; then
  sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5"
  },
  "registry-mirrors": [
    "https://docker.1panel.live",
    "https://hub.atomgit.com",
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run",
    "https://dockerproxy.com"
  ],
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 5
}
EOF
  sudo systemctl restart docker
else
  log "  daemon.json 已存在，不覆盖；如需使用新镜像加速请手动调整"
fi

# ---------- 6. 创建 hermes 数据目录 & env 目录（归属于 $DEPLOY_USER）----------
log "准备数据目录 $HERMES_DATA_DIR"
sudo -u "$DEPLOY_USER" mkdir -p "$HERMES_DATA_DIR"
sudo -u "$DEPLOY_USER" mkdir -p "$HERMES_ENV_DIR"
sudo chmod 700 "$HERMES_ENV_DIR"

# ~/.hermes/.env 模板（如不存在则生成，已存在不覆盖）
if ! sudo test -f "$HERMES_DATA_DIR/.env"; then
  log "生成 $HERMES_DATA_DIR/.env 模板，请稍后填入真实 API Key"
  RANDOM_KEY="$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p -c 64)"
  # 启用 HTTPS 时 hermes 只本地监听，公网访问走 Nginx 443 反代
  if [ "$ENABLE_HTTPS" = "1" ]; then
    API_HOST_VAL="127.0.0.1"
  else
    API_HOST_VAL="0.0.0.0"
  fi
  sudo -u "$DEPLOY_USER" tee "$HERMES_DATA_DIR/.env" >/dev/null <<EOF
# ============================================================================
# hermes API Server 对外暴露配置（被 codeshark 后端通过公网访问）
# ============================================================================
API_SERVER_HOST=${API_HOST_VAL}
API_SERVER_PORT=${HERMES_PORT}
# 必须设置，否则 hermes 拒绝非 loopback 绑定。codeshark 后端 HERMES_API_KEY 需用同一值
API_SERVER_KEY=${RANDOM_KEY}
# CORS：后端代理调用不需要，留空
API_SERVER_CORS_ORIGINS=

# ============================================================================
# 模型 Provider 凭证（按需填写，下方为常见示例）
# ============================================================================
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# DEEPSEEK_API_KEY=...
EOF
  sudo chmod 600 "$HERMES_DATA_DIR/.env"
  sudo chown "$DEPLOY_USER:$DEPLOY_USER" "$HERMES_DATA_DIR/.env"
  log "随机生成的 API_SERVER_KEY: $RANDOM_KEY"
  log "  → 请把它配置到 codeshark 后端 application.properties 的 HERMES_API_KEY"
else
  log "$HERMES_DATA_DIR/.env 已存在，跳过模板生成"
fi

# ~/env/hermes.env（部署用，存 MySQL 凭证与可选镜像仓库凭证）
if ! sudo test -f "$HERMES_ENV_DIR/hermes.env"; then
  log "生成 $HERMES_ENV_DIR/hermes.env（含 MySQL 随机密码）"
  MYSQL_ROOT_PWD="$(openssl rand -hex 24 2>/dev/null || head -c 24 /dev/urandom | xxd -p -c 48)"
  MYSQL_USER_PWD="$(openssl rand -hex 24 2>/dev/null || head -c 24 /dev/urandom | xxd -p -c 48)"
  sudo -u "$DEPLOY_USER" tee "$HERMES_ENV_DIR/hermes.env" >/dev/null <<EOF
# ============================================================================
# hermes-agent 部署凭证（docker-compose env_file 使用）
# ============================================================================

# ----- MySQL（容器 hermes-mysql 初始化 + gateway 连接使用）-----
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PWD}
MYSQL_DATABASE=hermes
MYSQL_USER=hermes
MYSQL_PASSWORD=${MYSQL_USER_PWD}

# ----- 私有镜像仓库凭证（使用阿里云 ACR，部署时 docker login，拉取 mysql 等镜像）-----
ACR_REGISTRY=${ACR_REGISTRY}
ACR_NAMESPACE=${ACR_NAMESPACE}
ACR_USERNAME=${ACR_USERNAME}
ACR_PASSWORD=${ACR_PASSWORD}
EOF
  sudo chmod 600 "$HERMES_ENV_DIR/hermes.env"
  sudo chown "$DEPLOY_USER:$DEPLOY_USER" "$HERMES_ENV_DIR/hermes.env"
  log "  MySQL 初始随机密码已写入 $HERMES_ENV_DIR/hermes.env（权限 600）"
else
  log "$HERMES_ENV_DIR/hermes.env 已存在，跳过模板生成"
  warn "  如该文件未包含 MYSQL_ROOT_PASSWORD/MYSQL_DATABASE/MYSQL_USER/MYSQL_PASSWORD，请手动补全"
fi

# MySQL 数据目录（mysql 容器首次启动会自动初始化 chown）
log "准备 MySQL 数据目录 $MYSQL_DATA_DIR"
sudo mkdir -p "$MYSQL_DATA_DIR"

# ---------- 7. Swap（hermes 镜像构建包含 npm + playwright，内存峰值较高）----------
if [ "${SWAP_SIZE_GB}" -gt 0 ] && [ ! -f /swapfile ]; then
  log "创建 ${SWAP_SIZE_GB}G swap"
  sudo fallocate -l "${SWAP_SIZE_GB}G" /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  if ! grep -q '^/swapfile' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
  fi
fi

# ---------- 8. HTTPS 反代（Nginx + certbot，仅在传入 HERMES_DOMAIN 时启用）----------
if [ "$ENABLE_HTTPS" = "1" ]; then
  log "启用 HTTPS 反代：$HERMES_DOMAIN"
  sudo apt-get install -y nginx certbot python3-certbot-nginx

  # webroot 目录供 ACME challenge 使用
  sudo mkdir -p /var/www/letsencrypt
  sudo chown -R www-data:www-data /var/www/letsencrypt

  CERT_DIR="/etc/letsencrypt/live/${HERMES_DOMAIN}"

  # ---- 阶段 1：如证书不存在，先写临时 80 站点 + webroot 拿证书 ----
  if ! sudo test -f "${CERT_DIR}/fullchain.pem"; then
    log "写临时 nginx 站点（仅 80）用于 ACME challenge"
    sudo tee /etc/nginx/sites-available/hermes >/dev/null <<EOF
server {
    listen 80;
    server_name ${HERMES_DOMAIN};
    location /.well-known/acme-challenge/ { root /var/www/letsencrypt; }
    location / { return 404; }
}
EOF
    sudo ln -sf /etc/nginx/sites-available/hermes /etc/nginx/sites-enabled/hermes
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx

    log "使用 certbot webroot 申请 Let's Encrypt 证书（需 DNS 已解析到本机）"
    if ! sudo certbot certonly --webroot -w /var/www/letsencrypt \
         -d "$HERMES_DOMAIN" --non-interactive --agree-tos -m "$CERTBOT_EMAIL"; then
      warn "certbot 签发失败，请排查后手动跑："
      warn "  sudo certbot certonly --webroot -w /var/www/letsencrypt -d $HERMES_DOMAIN -m $CERTBOT_EMAIL --agree-tos"
    fi
  else
    log "证书已存在：${CERT_DIR}/fullchain.pem"
  fi

  # ---- 阶段 2：写完整反代配置（443 SSE + 80 重定向）----
  if sudo test -f "${CERT_DIR}/fullchain.pem"; then
    log "写完整 nginx 反代配置（SSE 适配）"
    sudo tee /etc/nginx/sites-available/hermes >/dev/null <<EOF
server {
    listen 80;
    server_name ${HERMES_DOMAIN};
    location /.well-known/acme-challenge/ { root /var/www/letsencrypt; }
    location / { return 301 https://\$host\$request_uri; }
}

server {
    listen 443 ssl http2;
    server_name ${HERMES_DOMAIN};

    ssl_certificate     ${CERT_DIR}/fullchain.pem;
    ssl_certificate_key ${CERT_DIR}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # SSE 必需：关闭缓存与代理缓冲，保持 keep-alive
    proxy_buffering off;
    proxy_cache off;
    proxy_http_version 1.1;
    proxy_set_header Connection "";

    # SSE 长连接超时（与 codeshark 后端 readTimeout 600s 对齐）
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;

    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:${HERMES_PORT};
    }
}
EOF
    sudo nginx -t && sudo systemctl reload nginx
    log "HTTPS 反代就绪：https://${HERMES_DOMAIN}/v1/chat/completions"
  fi
fi

# ---------- 9. 防火墙（ufw，HTTPS 模式下仅放行 80/443，依靠 API_SERVER_KEY 鉴权）----------
if command -v ufw >/dev/null 2>&1; then
  log "配置 ufw"
  sudo ufw allow 22/tcp || true

  if [ "$ENABLE_HTTPS" = "1" ]; then
    # HTTPS 模式：公网放行 80（ACME 续签）+ 443（hermes 入口），全靠 Bearer Token 鉴权
    log "放行 80/tcp（ACME http-01）与 443/tcp (HTTPS)"
    sudo ufw allow 80/tcp comment "acme http-01" || true
    sudo ufw allow 443/tcp comment "hermes-https" || true
  else
    # 非 HTTPS 模式：直接暴露 hermes 端口到公网（不推荐）
    warn "未启用 HTTPS，hermes 端口 $HERMES_PORT 将明文暴露公网。强烈建议传入 HERMES_DOMAIN 启用 HTTPS。"
    sudo ufw allow "$HERMES_PORT/tcp" comment "hermes (plain http, NOT recommended)" || true
  fi
  if ! sudo ufw status | grep -q "Status: active"; then
    warn "ufw 尚未启用，待你确认放行规则正确后执行：sudo ufw enable"
  fi
fi

# ---------- 9. 为 $DEPLOY_USER 生成 SSH 部署密钥 ----------
SSH_DIR="${DEPLOY_USER_HOME}/.ssh"
DEPLOY_KEY_PATH="${SSH_DIR}/hermes_deploy"

sudo -u "$DEPLOY_USER" mkdir -p "$SSH_DIR"
sudo chmod 700 "$SSH_DIR"

if ! sudo test -f "$DEPLOY_KEY_PATH"; then
  log "为 $DEPLOY_USER 生成 SSH 部署密钥（ed25519）"
  sudo -u "$DEPLOY_USER" ssh-keygen -t ed25519 -f "$DEPLOY_KEY_PATH" -N '' -C "hermes-deploy@$(hostname)" >/dev/null
else
  log "$DEPLOY_KEY_PATH 已存在，跳过生成"
fi

# 将公钥追加到 authorized_keys（如未在列表中）
AUTH_KEYS="${SSH_DIR}/authorized_keys"
PUB_KEY_CONTENT="$(sudo cat "${DEPLOY_KEY_PATH}.pub")"
if ! sudo test -f "$AUTH_KEYS" || ! sudo grep -qF "$PUB_KEY_CONTENT" "$AUTH_KEYS" 2>/dev/null; then
  echo "$PUB_KEY_CONTENT" | sudo -u "$DEPLOY_USER" tee -a "$AUTH_KEYS" >/dev/null
  sudo chmod 600 "$AUTH_KEYS"
fi

log "SSH 部署密钥已就绪："
log "  公钥（已加入 authorized_keys）: ${DEPLOY_KEY_PATH}.pub"
log "  私钥（需手动复制到 GH secret HERMES_DEPLOY_KEY）: ${DEPLOY_KEY_PATH}"
log "  查看私钥内容： sudo cat ${DEPLOY_KEY_PATH}"
# ---------- 10. 总结 ----------
echo
log "========== 安装完成 =========="
log "部署用户:     $DEPLOY_USER  ($(id "$DEPLOY_USER" 2>/dev/null || echo 'unknown'))"
log "Docker:       $(docker --version 2>/dev/null || echo '需重新登录后可用')"
log "Compose:      $(docker compose version 2>/dev/null || echo '需重新登录后可用')"
log "数据目录:     $HERMES_DATA_DIR"
log "  → .env:    $HERMES_DATA_DIR/.env （请检查 API_SERVER_KEY 和模型凭证）"
log "部署凭证目录: $HERMES_ENV_DIR"
log "  → hermes.env (MySQL 随机密码 + ACR 凭证模板)"
log "MySQL 数据目录: $MYSQL_DATA_DIR"
log "API 端口:     $HERMES_PORT"
if [ "$ENABLE_HTTPS" = "1" ]; then
  log "HTTPS 入口:    https://${HERMES_DOMAIN}"
  log "  → codeshark 后端 HERMES_BASE_URL=https://${HERMES_DOMAIN}"
else
  log "HTTPS:        未启用（未传入 HERMES_DOMAIN）"
fi
log "SSH 私钥:     $DEPLOY_KEY_PATH"
echo
log "下一步："
log "  1. 复制私钥到 GH secret HERMES_DEPLOY_KEY： sudo cat $DEPLOY_KEY_PATH"
log "  2. 在 GH environment 'hermes-product' 配置："
log "       vars.HERMES_HOST = <本机公网 IP / 域名>"
log "       vars.HERMES_USER = $DEPLOY_USER"
log "  3. 确保 ACR 中已存在以下镜像（docker-image-sync 规则：源路径 / 转 -）："
log "       • ${ACR_REGISTRY}/${ACR_NAMESPACE}/mysql:8.0"
log "       • ${ACR_REGISTRY}/${ACR_NAMESPACE}/debian:13.4"
log "       • ${ACR_REGISTRY}/${ACR_NAMESPACE}/ghcr.io-astral-sh-uv:0.11.6-python3.13-trixie"
log "       • ${ACR_REGISTRY}/${ACR_NAMESPACE}/tianon-gosu:1.19-trixie"
log "  4. push 到 master 触发 build-deploy-server.yml 完成首次部署"

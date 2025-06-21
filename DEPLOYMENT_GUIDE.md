# 🚀 TDD Discord Bot - デプロイメントガイド

このガイドでは、TDD Discord Botを本番環境にデプロイする方法を説明します。

## 📋 目次

1. [デプロイメント戦略](#デプロイメント戦略)
2. [インフラ要件](#インフラ要件)
3. [クラウドプラットフォーム](#クラウドプラットフォーム)
4. [コンテナデプロイメント](#コンテナデプロイメント)
5. [VPSデプロイメント](#vpsデプロイメント)
6. [モニタリング設定](#モニタリング設定)
7. [バックアップ・復旧](#バックアップ復旧)
8. [セキュリティ設定](#セキュリティ設定)

---

## デプロイメント戦略

### 🎯 推奨デプロイメント方法

| 規模 | ユーザー数 | 推奨プラットフォーム | 月間コスト目安 |
|------|-----------|-------------------|---------------|
| **個人・小規模** | ~100人 | VPS (DigitalOcean/Vultr) | $5-20 |
| **中規模** | 100-1000人 | Heroku/Railway/Fly.io | $10-50 |
| **大規模** | 1000人以上 | AWS/GCP/Azure | $50-200+ |

### 📊 アーキテクチャパターン

#### パターンA: シンプル構成 (小規模)
```
┌─────────────────┐
│   Discord Bot   │
├─────────────────┤
│ Python + Redis  │
│ Single Server   │
└─────────────────┘
```

#### パターンB: 冗長構成 (中〜大規模)
```
┌─────────────┐    ┌─────────────┐
│ Load Balancer│    │ Monitoring  │
└─────┬───────┘    └─────────────┘
      │
┌─────▼───────┐    ┌─────────────┐
│ Bot Instance│    │   Redis     │
│    (Primary)│◄───┤  Cluster    │
└─────────────┘    └─────────────┘
┌─────────────┐
│ Bot Instance│
│  (Standby)  │
└─────────────┘
```

---

## インフラ要件

### 🖥️ 最小システム要件

| リソース | 最小 | 推奨 | 大規模 |
|----------|------|------|--------|
| **CPU** | 1 vCPU | 2 vCPU | 4+ vCPU |
| **メモリ** | 512MB | 1GB | 2GB+ |
| **ストレージ** | 5GB | 10GB | 20GB+ |
| **帯域幅** | 無制限 | 無制限 | 無制限 |

### 🔧 必須ソフトウェア

- **Python 3.8+** (推奨: 3.11)
- **Redis 6.0+** (レート制限・キャッシュ用)
- **FFmpeg** (音声・動画処理用)
- **Git** (デプロイメント用)

### 🌐 ネットワーク要件

| サービス | ポート | 方向 | 用途 |
|----------|--------|------|------|
| Discord Gateway | 443 (HTTPS) | Outbound | Bot通信 |
| OpenAI API | 443 (HTTPS) | Outbound | AI処理 |
| Redis | 6379 | Internal | データベース |
| SSH | 22 | Inbound | 管理アクセス |

---

## クラウドプラットフォーム

### 1. Railway (推奨・簡単)

**特徴**: Git連携、自動デプロイ、簡単設定

**デプロイ手順**:

1. **Railwayアカウント作成**
   ```bash
   # Railway CLI インストール
   npm install -g @railway/cli
   railway login
   ```

2. **プロジェクト作成**
   ```bash
   railway new
   cd your-project
   railway link
   ```

3. **環境変数設定**
   ```bash
   # Railway Web UIまたはCLIで設定
   railway variables set DISCORD_TOKEN=your_token
   railway variables set OPENAI_API_KEY=your_key
   railway variables set REDIS_URL=redis://redis:6379
   ```

4. **Redisサービス追加**
   ```bash
   railway add redis
   ```

5. **デプロイ**
   ```bash
   git add .
   git commit -m "Deploy TDD Bot"
   git push origin main
   railway deploy
   ```

**`railway.json`** (プロジェクトルートに配置):
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "python tdd_bot.py",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

---

### 2. Heroku

**特徴**: 老舗PaaS、豊富なアドオン

**デプロイ手順**:

1. **Heroku設定ファイル作成**

**`Procfile`** (プロジェクトルートに配置):
```
worker: python tdd_bot.py
```

**`runtime.txt`**:
```
python-3.11.0
```

**`Aptfile`** (FFmpeg用):
```
ffmpeg
```

2. **Herokuアプリ作成**
   ```bash
   heroku create your-bot-name
   heroku buildpacks:add --index 1 heroku-community/apt
   heroku buildpacks:add --index 2 heroku/python
   ```

3. **Redis追加**
   ```bash
   heroku addons:create heroku-redis:mini
   ```

4. **環境変数設定**
   ```bash
   heroku config:set DISCORD_TOKEN=your_token
   heroku config:set OPENAI_API_KEY=your_key
   ```

5. **デプロイ**
   ```bash
   git push heroku main
   heroku ps:scale worker=1
   ```

---

### 3. DigitalOcean App Platform

**特徴**: VPS感覚で使えるPaaS

**`.do/app.yaml`**:
```yaml
name: tdd-discord-bot
services:
- name: bot
  source_dir: /
  github:
    repo: your-username/discord-bot-dev
    branch: main
  run_command: python tdd_bot.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: DISCORD_TOKEN
    value: your_token
    type: SECRET
  - key: OPENAI_API_KEY
    value: your_key
    type: SECRET
databases:
- name: redis
  engine: REDIS
  version: "6"
  size_slug: db-s-1vcpu-1gb
```

---

## コンテナデプロイメント

### 🐳 Docker設定

**`Dockerfile`**:
```dockerfile
FROM python:3.11-slim

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    redis-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ設定
WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルのコピー
COPY . .

# ユーザー権限でアプリケーション実行
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# アプリケーション実行
CMD ["python", "tdd_bot.py"]
```

**`docker-compose.yml`**:
```yaml
version: '3.8'

services:
  bot:
    build: .
    restart: unless-stopped
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

**デプロイ手順**:
```bash
# 環境変数ファイル作成
cp .env.template .env
# .envファイルを編集

# Docker Compose起動
docker-compose up -d

# ログ確認
docker-compose logs -f bot
```

---

## VPSデプロイメント

### 🖥️ Ubuntu 22.04 LTS での手順

**1. 初期設定**
```bash
# VPSにSSH接続
ssh root@your-vps-ip

# システム更新
apt update && apt upgrade -y

# 必要パッケージインストール
apt install -y python3.11 python3.11-venv python3-pip \
               redis-server ffmpeg git nginx supervisor \
               certbot python3-certbot-nginx
```

**2. アプリケーション用ユーザー作成**
```bash
# botユーザー作成
useradd -m -s /bin/bash botuser
usermod -aG sudo botuser

# SSH鍵設定（セキュリティ向上）
sudo -u botuser mkdir -p /home/botuser/.ssh
# 公開鍵を ~/.ssh/authorized_keys に追加
```

**3. アプリケーションデプロイ**
```bash
# botユーザーに切り替え
sudo -u botuser -i

# リポジトリクローン
git clone https://github.com/your-username/discord-bot-dev.git
cd discord-bot-dev

# Python仮想環境作成
python3.11 -m venv .venv
source .venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.template .env
# .envファイルを編集
```

**4. サービス設定**

**`/etc/supervisor/conf.d/tdd-bot.conf`**:
```ini
[program:tdd-bot]
command=/home/botuser/discord-bot-dev/.venv/bin/python /home/botuser/discord-bot-dev/tdd_bot.py
directory=/home/botuser/discord-bot-dev
user=botuser
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/tdd-bot.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
environment=PATH="/home/botuser/discord-bot-dev/.venv/bin"
```

**5. サービス開始**
```bash
# Supervisor設定リロード
sudo supervisorctl reread
sudo supervisorctl update

# Bot起動
sudo supervisorctl start tdd-bot

# ステータス確認
sudo supervisorctl status
```

---

## モニタリング設定

### 📊 基本監視

**1. システムリソース監視**
```bash
# htop インストール
sudo apt install htop

# システム情報確認
htop
df -h
free -h
```

**2. ログ監視**
```bash
# Bot ログの確認
sudo tail -f /var/log/tdd-bot.log

# Redis ログの確認
sudo tail -f /var/log/redis/redis-server.log

# システムログ確認
sudo journalctl -u tdd-bot -f
```

**3. プロセス監視スクリプト**

**`monitor.sh`**:
```bash
#!/bin/bash

# Bot プロセス確認
if ! pgrep -f "tdd_bot.py" > /dev/null; then
    echo "$(date): Bot process not found! Restarting..."
    sudo supervisorctl restart tdd-bot
fi

# Redis 確認
if ! redis-cli ping > /dev/null 2>&1; then
    echo "$(date): Redis not responding! Restarting..."
    sudo systemctl restart redis-server
fi

# ディスク使用量確認
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "$(date): Disk usage is ${DISK_USAGE}%! Cleaning up..."
    # ログファイルローテーション
    sudo logrotate -f /etc/logrotate.conf
fi
```

**Cron設定** (5分間隔で監視):
```bash
# crontab編集
crontab -e

# 以下を追加
*/5 * * * * /home/botuser/discord-bot-dev/monitor.sh >> /home/botuser/monitor.log 2>&1
```

### 🔔 アラート設定

**Discord Webhook アラート**:
```python
# alert.py
import requests
import json

def send_discord_alert(message):
    webhook_url = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
    
    data = {
        "embeds": [{
            "title": "🚨 Bot Alert",
            "description": message,
            "color": 16711680,  # Red
            "timestamp": datetime.now().isoformat()
        }]
    }
    
    requests.post(webhook_url, data=json.dumps(data), 
                 headers={"Content-Type": "application/json"})
```

---

## バックアップ・復旧

### 💾 バックアップ戦略

**1. 設定ファイル**
```bash
# 設定ファイルのバックアップ
tar -czf config-backup-$(date +%Y%m%d).tar.gz \
    .env \
    /etc/supervisor/conf.d/tdd-bot.conf \
    /etc/nginx/sites-available/default
```

**2. Redisデータ**
```bash
# Redis データのバックアップ
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /backup/redis-$(date +%Y%m%d).rdb
```

**3. 自動バックアップスクリプト**

**`backup.sh`**:
```bash
#!/bin/bash

BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d_%H%M%S)

# バックアップディレクトリ作成
mkdir -p $BACKUP_DIR

# アプリケーションファイル
tar -czf $BACKUP_DIR/app-$DATE.tar.gz \
    /home/botuser/discord-bot-dev \
    --exclude=".venv" \
    --exclude="__pycache__" \
    --exclude=".git"

# Redis データ
redis-cli BGSAVE
sleep 5
cp /var/lib/redis/dump.rdb $BACKUP_DIR/redis-$DATE.rdb

# 設定ファイル
tar -czf $BACKUP_DIR/config-$DATE.tar.gz \
    /etc/supervisor/conf.d/tdd-bot.conf \
    /etc/nginx/sites-available/

# 古いバックアップ削除（30日以上）
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +30 -delete

echo "Backup completed: $DATE"
```

**Cron設定** (毎日午前3時):
```bash
0 3 * * * /home/botuser/discord-bot-dev/backup.sh >> /var/log/backup.log 2>&1
```

### 🔄 復旧手順

**1. アプリケーション復旧**
```bash
# サービス停止
sudo supervisorctl stop tdd-bot

# バックアップから復旧
cd /home/botuser
tar -xzf /backup/app-YYYYMMDD_HHMMSS.tar.gz

# 権限修正
chown -R botuser:botuser discord-bot-dev

# サービス再開
sudo supervisorctl start tdd-bot
```

**2. Redis復旧**
```bash
# Redis停止
sudo systemctl stop redis-server

# データファイル復旧
sudo cp /backup/redis-YYYYMMDD_HHMMSS.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb

# Redis再開
sudo systemctl start redis-server
```

---

## セキュリティ設定

### 🔒 基本セキュリティ

**1. ファイアウォール設定**
```bash
# UFW有効化
sudo ufw enable

# SSH許可
sudo ufw allow ssh

# 不要ポート閉鎖
sudo ufw deny 6379  # Redis (内部接続のみ)

# ステータス確認
sudo ufw status
```

**2. SSH鍵認証**
```bash
# パスワード認証無効化
sudo nano /etc/ssh/sshd_config

# 以下を設定
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no

# SSH再起動
sudo systemctl restart ssh
```

**3. 自動セキュリティ更新**
```bash
# unattended-upgrades設定
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 🛡️ アプリケーションセキュリティ

**1. 環境変数保護**
```bash
# .env ファイル権限設定
chmod 600 .env

# 所有者確認
ls -la .env
# -rw------- 1 botuser botuser 456 Jan 1 12:00 .env
```

**2. ログファイル保護**
```bash
# ログディレクトリ権限設定
sudo chmod 750 /var/log
sudo chown root:adm /var/log/tdd-bot.log
sudo chmod 640 /var/log/tdd-bot.log
```

**3. Redis セキュリティ**

**`/etc/redis/redis.conf`** 設定:
```conf
# 外部接続無効化
bind 127.0.0.1

# パスワード設定
requirepass your_strong_redis_password

# 危険コマンド無効化
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

---

## 📈 スケーリング戦略

### 水平スケーリング

**ロードバランサー設定** (Nginx):
```nginx
upstream tdd_bot {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://tdd_bot;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 垂直スケーリング

**リソース監視とアラート**:
```bash
# CPU使用率監視
vmstat 1

# メモリ使用率監視
free -m

# ディスクI/O監視
iostat -x 1
```

---

## 🔄 継続的デプロイメント

### GitHub Actions設定

**`.github/workflows/deploy.yml`**:
```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Run Tests
      run: |
        pip install -r requirements.txt
        python run_tests.py
    
    - name: Deploy to Server
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /home/botuser/discord-bot-dev
          git pull origin main
          source .venv/bin/activate
          pip install -r requirements.txt
          sudo supervisorctl restart tdd-bot
```

---

**Deployment Guide v1.0 - Ready for Production! 🚀**
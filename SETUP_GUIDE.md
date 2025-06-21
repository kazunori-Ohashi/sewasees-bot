# 🚀 TDD Discord Bot - 詳細セットアップガイド

このガイドでは、TDD Discord Botの完全なセットアップ手順を説明します。

## 📋 目次

1. [前提条件の確認](#前提条件の確認)
2. [システム依存関係のインストール](#システム依存関係のインストール)
3. [プロジェクトセットアップ](#プロジェクトセットアップ)
4. [Discord Bot設定](#discord-bot設定)
5. [OpenAI API設定](#openai-api設定)
6. [環境変数設定](#環境変数設定)
7. [Redis設定](#redis設定)
8. [テスト実行](#テスト実行)
9. [Bot起動](#bot起動)
10. [トラブルシューティング](#トラブルシューティング)

---

## 1. 前提条件の確認

### 必要なアカウント

- ✅ **Discord Developer Account**: [Discord Developer Portal](https://discord.com/developers/applications)
- ✅ **OpenAI Account**: [OpenAI Platform](https://platform.openai.com/)
- ✅ **管理者権限のDiscordサーバー**: Botをテストするため

### 必要なソフトウェア

| ソフトウェア | 最小バージョン | 推奨バージョン | 用途 |
|-------------|---------------|---------------|------|
| Python | 3.8+ | 3.11+ | Bot実行環境 |
| Git | 2.0+ | 最新 | ソースコード管理 |
| Redis | 6.0+ | 7.0+ | レート制限・キャッシュ |
| FFmpeg | 4.0+ | 6.0+ | 音声・動画処理 |

---

## 2. システム依存関係のインストール

### macOS (Homebrew使用)

```bash
# Homebrewがインストールされていない場合
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 必要なパッケージをインストール
brew update
brew install python@3.11 redis ffmpeg git

# Redisの自動起動設定（オプション）
brew services start redis
```

### Ubuntu/Debian

```bash
# パッケージリストを更新
sudo apt update && sudo apt upgrade -y

# 必要なパッケージをインストール
sudo apt install -y python3.11 python3.11-venv python3-pip \
                    redis-server ffmpeg git curl

# Redisサービスを開始・有効化
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### Windows (推奨: WSL2使用)

```powershell
# WSL2のインストール（管理者権限で実行）
wsl --install

# WSL2でUbuntuを起動後、上記Ubuntu手順を実行
```

### Windows ネイティブ（非推奨）

1. **Python**: [python.org](https://python.org) からPython 3.11をダウンロード
2. **Redis**: [Redis for Windows](https://github.com/microsoftarchive/redis/releases)
3. **FFmpeg**: [FFmpeg builds](https://ffmpeg.org/download.html#build-windows)
4. **Git**: [Git for Windows](https://git-scm.com/download/win)

---

## 3. プロジェクトセットアップ

### リポジトリクローン

```bash
# プロジェクトをクローン
git clone <repository-url>
cd discord-bot-dev

# または既存のディレクトリがある場合
cd discord-bot-dev
```

### Python仮想環境の作成

```bash
# 仮想環境を作成
python3.11 -m venv .venv

# 仮想環境を有効化
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 仮想環境が有効化されていることを確認
which python  # macOS/Linux
where python   # Windows
# -> .venv内のpythonパスが表示されるはず
```

### 依存関係のインストール

```bash
# pipをアップグレード
pip install --upgrade pip

# プロジェクト依存関係をインストール
pip install -r requirements.txt

# インストール確認
pip list | grep -E "(discord|openai|redis|pdfminer)"
```

---

## 4. Discord Bot設定

### 4.1 Botアプリケーションの作成

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. **「New Application」** をクリック
3. アプリケーション名を入力（例: `TDD-Content-Bot`）
4. **「Create」** をクリック

### 4.2 Botユーザーの作成

1. 左メニューから **「Bot」** を選択
2. **「Add Bot」** → **「Yes, do it!」** をクリック
3. **「Token」** セクションで **「Copy」** をクリックしてトークンを保存
   - ⚠️ **重要**: このトークンは秘密情報です。他人と共有しないでください

### 4.3 Bot権限の設定

**「OAuth2」** → **「URL Generator」** で以下を設定:

#### Scopes (必須)
- ✅ `bot`
- ✅ `applications.commands`

#### Bot Permissions (必須)
- ✅ **Send Messages** - メッセージ送信
- ✅ **Use Slash Commands** - スラッシュコマンド使用
- ✅ **Attach Files** - ファイル添付
- ✅ **Read Message History** - メッセージ履歴読み取り
- ✅ **Add Reactions** - リアクション追加
- ✅ **Use External Emojis** - 外部絵文字使用（オプション）

### 4.4 Botをサーバーに招待

1. 生成されたURLをコピー
2. URLをブラウザで開き、Botを管理者権限のあるサーバーに招待
3. 必要な権限を確認して **「認証」** をクリック

---

## 5. OpenAI API設定

### 5.1 APIキーの取得

1. [OpenAI Platform](https://platform.openai.com/) にログイン
2. **「API Keys」** → **「Create new secret key」** をクリック
3. キーに名前を付け（例: `discord-bot-key`）、**「Create secret key」** をクリック
4. 表示されるAPIキーをコピーして保存
   - ⚠️ **重要**: このキーは再表示されません

### 5.2 利用制限・料金の確認

```bash
# APIキーのテスト（オプション）
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.openai.com/v1/models
```

---

## 6. 環境変数設定

### 6.1 .envファイルの作成

```bash
# テンプレートをコピー
cp .env.template .env

# .envファイルを編集
nano .env  # または vim, code, など
```

### 6.2 基本設定

```bash
# === 必須設定 ===
DISCORD_TOKEN=your_discord_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here

# === Redis設定 ===
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=password_if_needed

# === Bot動作設定 ===
DAILY_RATE_LIMIT=5                    # 無料ユーザーの日次制限
PREMIUM_ROLE_NAME=premium             # Premiumロール名（小文字）

# === 管理機能（オプション） ===
MODERATOR_CHANNEL_ID=123456789012345678  # モデレーターログチャンネルID

# === デバッグ ===
DEBUG=false                           # デバッグログの有効/無効
```

### 6.3 モデレーターチャンネルの設定（オプション）

管理者ログを受信したい場合:

1. Discordサーバーで専用チャンネルを作成（例: `#bot-logs`）
2. **開発者モード** を有効化：
   - Discord設定 → 詳細設定 → 開発者モード をON
3. チャンネルを右クリック → **「IDをコピー」**
4. `.env`の`MODERATOR_CHANNEL_ID`に設定

---

## 7. Redis設定

### 7.1 Redis起動の確認

```bash
# Redisが起動しているか確認
redis-cli ping
# 期待される出力: PONG

# Redisが起動していない場合
# macOS (Homebrew):
brew services start redis

# Ubuntu/Debian:
sudo systemctl start redis-server

# 手動起動:
redis-server
```

### 7.2 Redis接続テスト

```bash
# 基本的な動作テスト
redis-cli
127.0.0.1:6379> set test "hello"
127.0.0.1:6379> get test
127.0.0.1:6379> del test
127.0.0.1:6379> exit
```

---

## 8. テスト実行

### 8.1 依存性と基本機能のテスト

```bash
# 仮想環境が有効化されていることを確認
source .venv/bin/activate  # 必要に応じて

# TDDテストランナーを実行
python run_tests.py
```

**期待される出力:**
```
🤖 TDD Discord Bot テストランナー
✅ 仮想環境が有効です
✅ 依存関係のインストール
✅ Bot モジュールのインポートテスト
✅ ユニットテスト実行
✅ 依存性チェック実行成功
✅ すべての基本テストがパスしました
```

### 8.2 個別テストの実行

```bash
# 特定のテストのみ実行
pytest tests/unit/test_limit.py -v
pytest tests/security/test_mime.py -v
```

---

## 9. Bot起動

### 9.1 最終チェック

起動前に以下を確認:

- ✅ `.env`ファイルに正しい値が設定されている
- ✅ Redisサーバーが起動している
- ✅ 仮想環境が有効化されている
- ✅ Bot がDiscordサーバーに招待されている

### 9.2 Bot起動

```bash
# Bot起動
python tdd_bot.py
```

**期待される出力:**
```
INFO:tdd_bot:✅ Redis connection OK
INFO:tdd_bot:✅ All dependencies check passed
INFO:tdd_bot:TDDBot#1234 has connected to Discord!
INFO:tdd_bot:Synced 2 command(s)
```

### 9.3 動作確認

Discordサーバーで以下をテスト:

1. **スラッシュコマンドの確認**:
   - `/article` コマンドが表示されるか
   - `/usage` コマンドが表示されるか

2. **基本動作テスト**:
   ```
   /usage
   ```
   → 使用回数が表示されるか確認

3. **ファイル処理テスト**:
   - 小さなテキストファイルで `/article` を実行
   - Markdown記事が生成されるか確認

---

## 10. トラブルシューティング

### 🔴 よくある問題と解決法

#### Bot がオンラインにならない

**症状**: Bot がDiscordでオフライン表示
```bash
# .envファイルの確認
cat .env | grep DISCORD_TOKEN
# 出力: DISCORD_TOKEN=actual_token_value

# Tokenの形式確認（MTAで始まる必要がある）
echo $DISCORD_TOKEN | cut -c1-3
# 期待される出力: MTA
```

#### Redis接続エラー

**症状**: `Redis server is not available`
```bash
# Redisプロセス確認
ps aux | grep redis
# または
systemctl status redis-server

# Redisポート確認
netstat -tlnp | grep 6379
# または
ss -tlnp | grep 6379

# Redis再起動
sudo systemctl restart redis-server
```

#### ffmpeg not found

**症状**: `ffmpeg is not installed or not in PATH`
```bash
# ffmpegインストール確認
which ffmpeg
ffmpeg -version

# PATHの確認
echo $PATH | tr ':' '\n' | grep -E "(usr/bin|usr/local/bin)"

# macOSでの再インストール
brew reinstall ffmpeg

# Ubuntuでの再インストール
sudo apt purge ffmpeg
sudo apt install ffmpeg
```

#### OpenAI API エラー

**症状**: `Invalid API key` または `Rate limit exceeded`
```bash
# APIキー形式の確認（sk-で始まる必要がある）
echo $OPENAI_API_KEY | cut -c1-3
# 期待される出力: sk-

# APIキー接続テスト
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models | head -n 20
```

#### 権限エラー

**症状**: Bot がメッセージを送信できない
1. Discord Developer Portal でBot権限を再確認
2. サーバーでのBot ロール権限を確認
3. チャンネル固有の権限設定を確認

#### 仮想環境の問題

**症状**: `ModuleNotFoundError` 
```bash
# 仮想環境の確認
which python
# 期待される出力: /path/to/project/.venv/bin/python

# 仮想環境の再作成
deactivate
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 📞 サポート情報

**エラー報告時に含める情報:**
- OS・バージョン
- Python バージョン (`python --version`)
- エラーメッセージ全文
- 実行したコマンド
- `.env` ファイルの内容（秘密情報は除く）

**ログファイルの場所:**
- Bot ログ: コンソール出力
- Redis ログ: `/var/log/redis/redis-server.log` (Ubuntu)
- システムログ: `journalctl -u redis-server` (systemd)

---

## 🎉 セットアップ完了

セットアップが完了したら、以下のドキュメントも参照してください:

- **[API リファレンス](API_REFERENCE.md)** - 詳細な機能説明
- **[デプロイメントガイド](DEPLOYMENT_GUIDE.md)** - 本番環境への展開
- **[メインREADME](TDD_BOT_README.md)** - 概要と基本的な使用方法

---

**Happy Coding! 🤖✨**
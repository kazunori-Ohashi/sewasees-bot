# TDD Discord Bot

ファイル（テキスト・PDF・音声・動画）から自動でMarkdown記事を生成するDiscord Botです。OpenAI GPT-4o-miniとWhisperを活用し、PREP法・PAS法による構造化された記事作成をサポートします。

## 🚀 主な機能

### スラッシュコマンド
- **`/article`** - ファイルからMarkdown記事を生成
  - `style`: prep（PREP法）/ pas（PAS法）
  - `include_tldr`: 要約の有無
- **`/tldr`** - ファイルから要約（TLDR）を生成
- **`/insert`** - 次のメッセージをMarkdown形式に整形
- **`/help`** - 使い方ガイド
- **`/usage`** - 今日の使用回数確認

### リアクション機能
- **🎤** - 音声・動画ファイルの自動文字起こし
- **❤️** - ツイートプレビュー生成

### メール連携
- **`/register_email`** - メールアドレス登録
- **`/confirm_email`** - メール認証
- **`/resend_result`** - 直近の結果をメール送信

## 📁 対応ファイル形式

| 形式 | 拡張子 | 処理方法 |
|------|---------|----------|
| テキスト | `.txt`, `.md` | 直接読み込み |
| PDF | `.pdf` | pdfminer.six |
| 音声 | `.mp3`, `.wav`, `.m4a`, `.ogg` | Whisper API |
| 動画 | `.mp4`, `.webm` | FFmpeg + Whisper |

## 🛠️ セットアップ

### 必要な依存関係

#### Pythonパッケージ
```bash
pip install discord.py redis openai python-dotenv pdfminer.six PyYAML
```

#### システム要件
- **FFmpeg** - 動画処理用
- **Redis Server** - レート制限管理用

### 環境変数設定

`.env`ファイルを作成し、以下を設定：

```env
# 必須
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key

# Redis設定（オプション）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# レート制限設定
DAILY_RATE_LIMIT=5
PREMIUM_ROLE_NAME=premium

# メール機能（オプション）
EMAIL_RECIPIENT=your_email@example.com
EMAIL_SENDER=bot@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASS=your_smtp_password

# ログ設定
MODERATOR_CHANNEL_ID=your_moderator_channel_id
```

### Discord Bot設定

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーション作成
2. Bot作成してトークンを取得
3. 必要な権限：
   - `Send Messages`
   - `Use Slash Commands`
   - `Add Reactions`
   - `Attach Files`

## 🚀 起動方法

```bash
python tdd_bot.py
```

### 起動時チェック項目
- Discord Token
- OpenAI API Key
- Redis接続
- FFmpeg インストール

## 📊 利用制限

### 無料ユーザー
- **日次制限**: 5回
- **ファイルサイズ**: 10MB（音声・動画は20MB）

### Premiumユーザー
- **日次制限**: 無制限
- **ファイルサイズ**: 50MB

## 🔧 技術仕様

### アーキテクチャ
- **単一ファイル設計** - `tdd_bot.py`にすべての機能を統合
- **非同期処理** - asyncio使用でノンブロッキングI/O
- **TDD実装** - テスト駆動開発によるコード実装

### セキュリティ
- MIMEタイプ検証
- 実行ファイル拒否
- ファイルサイズ制限
- レート制限（Redis）

### AI生成機能
- **記事生成**: PREP法・PAS法による構造化
- **要約生成**: 3-5箇条書きでの要約
- **文字起こし**: Whisper APIによる高精度変換

## 📝 使用例

### 1. PDFから記事生成
```
/article style:prep include_tldr:true
```
PDFファイルを添付して実行

### 2. 音声ファイルの文字起こし
音声ファイルに🎤リアクションを追加

### 3. テキスト整形
```
/insert
```
実行後、次のメッセージが自動でMarkdown整形される

## 🤝 サポート

- **問題報告**: [Issues](https://github.com/kazunori-Ohashi/sewasees-bot/issues)
- **バージョン**: v2.0.0
- **作成者**: 大橋和則

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

**注意**: `.env`ファイルはGitHubにコミットされません。本番環境では適切な環境変数管理を行ってください。
# TDD Discord Bot - プログラム仕様書

## 📋 目次

1. [概要](#概要)
2. [クラス仕様](#クラス仕様)
3. [メソッド詳細仕様](#メソッド詳細仕様)
4. [関数仕様](#関数仕様)
5. [データ構造仕様](#データ構造仕様)
6. [スラッシュコマンドワークフロー](#スラッシュコマンドワークフロー)
7. [外部サービス統合](#外部サービス統合)

---

## 概要

TDD Discord Botは、ファイル処理とAIを活用したMarkdown記事生成を行うDiscord Botです。テスト駆動開発(TDD)手法で実装され、Rate Limiting対策、キャッシュシステム、包括的なモニタリング機能を備えています。

### アーキテクチャ概要
- **メインクラス**: `TDDBot` (Discord Bot本体)
- **コマンドハンドラ**: `TDDCog` (Discord Slash Commands)
- **ファイル処理**: 非同期処理によるマルチメディア対応
- **AI統合**: OpenAI GPT-4o-mini + Whisper API
- **Rate Limiting**: 分散タイミング + 包括的モニタリング

---

## クラス仕様

### 1. TDDBot クラス

#### 基本情報
```python
class TDDBot(commands.Bot):
    """TDD仕様に基づいたDiscord Bot"""
```

#### 継承関係
- **親クラス**: `discord.ext.commands.Bot`
- **MRO**: TDDBot → commands.Bot → discord.Client → object

#### プロパティ

| プロパティ名 | 型 | 説明 | 初期化 |
|-------------|-----|------|--------|
| `daily_rate_limit` | `int` | 日次使用制限数 | `os.getenv('DAILY_RATE_LIMIT', '5')` |
| `premium_role_name` | `str` | プレミアムロール名 | `os.getenv('PREMIUM_ROLE_NAME', 'premium')` |
| `moderator_channel_id` | `int` | モデレーターログチャンネルID | `os.getenv('MODERATOR_CHANNEL_ID')` |
| `openai_client` | `OpenAI` | OpenAI APIクライアント | `OpenAI(api_key=...)` |
| `redis_client` | `None` | Redisクライアント（現在無効） | `None` |

#### メソッド一覧

| メソッド名 | 戻り値型 | 説明 | アクセス |
|-----------|---------|------|---------|
| `__init__()` | `None` | コンストラクタ | public |
| `setup_hook()` | `None` | Bot起動時の初期化処理 | async public |
| `on_ready()` | `None` | Bot接続完了イベント | async event |
| `on_message(message)` | `None` | メッセージ受信イベント | async event |
| `on_raw_reaction_add(payload)` | `None` | リアクション追加イベント | async event |
| `on_command_error(ctx, error)` | `None` | コマンドエラーハンドリング | async event |
| `log_to_moderator(**kwargs)` | `None` | モデレーターログ送信 | async public |
| `is_premium_user(member)` | `bool` | プレミアムユーザー判定 | public |
| `process_text_file(content, filename)` | `str` | テキストファイル処理 | async public |
| `process_pdf_file(content)` | `str` | PDFファイル処理 | async public |
| `process_audio_file(content, filename)` | `str` | 音声ファイル処理 | async public |
| `process_video_file(content, filename)` | `str` | 動画ファイル処理 | async public |
| `generate_article(content, style)` | `str` | AI記事生成 | async public |
| `generate_tldr(content)` | `str` | TLDR要約生成 | async public |

### 2. TDDCog クラス

#### 基本情報
```python
class TDDCog(commands.Cog):
    """Discord Slash Commands のコマンドグループ"""
```

#### 継承関係
- **親クラス**: `discord.ext.commands.Cog`
- **MRO**: TDDCog → commands.Cog → object

#### プロパティ

| プロパティ名 | 型 | 説明 |
|-------------|-----|------|
| `bot` | `TDDBot` | Bot インスタンスへの参照 |

#### Slash Commands

| コマンド名 | パラメータ | 説明 | ハンドラメソッド |
|-----------|-----------|------|----------------|
| `/insert` | なし | マークダウン整形モード有効化 | `insert_command()` |
| `/help` | なし | ヘルプメッセージ表示 | `help_command()` |
| `/article` | `file`, `style`, `include_tldr` | ファイルから記事生成 | `article_command()` |
| `/usage` | なし | 使用回数確認 | `usage_command()` |
| `/tldr` | `file` | ファイルから要約生成 | `tldr_command()` |
| `/register_email` | `email` | メールアドレス登録 | `register_email_command()` |
| `/confirm_email` | `token` | メール認証 | `confirm_email_command()` |
| `/resend_result` | なし | 直近結果の再送信 | `resend_result_command()` |
| `/rate_stats` | なし | Rate Limiting統計表示 | `rate_stats_command()` |

### 3. SyncDictJSON クラス

#### 基本情報
```python
class SyncDictJSON(dict):
    """JSON ファイルと同期する辞書クラス"""
```

#### 継承関係
- **親クラス**: `dict`
- **MRO**: SyncDictJSON → dict → object

#### クラス変数

| 変数名 | 型 | 説明 |
|-------|-----|------|
| `_locks` | `dict` | ファイルパス別のロック辞書 |
| `_instances` | `dict` | インスタンス管理辞書 |

#### メソッド

| メソッド名 | 戻り値型 | 説明 | アクセス |
|-----------|---------|------|---------|
| `create(path)` | `SyncDictJSON` | インスタンス作成（シングルトン） | classmethod |
| `__init__(path, lock)` | `None` | コンストラクタ | public |
| `__setitem__(key, value)` | `None` | 要素設定とファイル同期 | public |
| `__delitem__(key)` | `None` | 要素削除とファイル同期 | public |
| `_flush()` | `None` | JSONファイルへの書き込み | private |

### 4. 例外クラス群

#### UsageLimitExceeded
```python
class UsageLimitExceeded(Exception):
    """使用回数制限超過例外"""
```

#### DependencyError
```python
class DependencyError(Exception):
    """システム依存関係エラー例外"""
```

#### UnsupportedFileType
```python
class UnsupportedFileType(Exception):
    """サポートされていないファイル形式例外"""
```

---

## メソッド詳細仕様

### TDDBot.on_message()

#### 概要
ユーザーメッセージを受信し、insert モードの処理を実行

#### シグネチャ
```python
async def on_message(self, message: discord.Message) -> None
```

#### 入力
- `message`: `discord.Message` - 受信したDiscordメッセージオブジェクト

#### 出力
- `None` - 戻り値なし（副作用による処理）

#### 処理フロー
1. **Bot メッセージフィルタリング**: `message.author.bot` チェック
2. **Insert モードチェック**: キャッシュから `insert_mode:{user_id}` を検索
3. **Rate Limiting チェック**: ユーザー制限確認
4. **AI処理**: OpenAI API でマークダウン整形
5. **結果送信**: Discord ファイル添付 + Embed
6. **メール送信**: 設定済みの場合、結果をメール送信
7. **モニタリング**: 処理完了をモデレーターログに記録

#### エラーハンドリング
- `UsageLimitExceeded`: 使用制限超過時の処理
- `OpenAI API Error`: タイムアウト・認証エラー対応
- `Discord API Error`: Rate Limiting 対応

#### Rate Limiting 対策
- **通知送信**: 2-5秒のランダム遅延
- **ファイル送信**: 3-7秒のランダム遅延
- **API呼び出し分散**: バースト防止

### TDDBot.process_audio_file()

#### 概要
音声ファイルをWhisper APIで文字起こし

#### シグネチャ
```python
async def process_audio_file(self, content: bytes, filename: str) -> str
```

#### 入力
- `content`: `bytes` - 音声ファイルのバイナリデータ
- `filename`: `str` - ファイル名（拡張子含む）

#### 出力
- `str` - 文字起こし結果のテキスト

#### 処理フロー
1. **一時ファイル作成**: バイナリデータを一時ファイルに保存
2. **Whisper API呼び出し**: OpenAI Whisper で音声認識
3. **結果取得**: 文字起こしテキストを取得
4. **クリーンアップ**: 一時ファイルの削除

#### エラーハンドリング
- `FileNotFoundError`: 一時ファイル作成失敗
- `OpenAI API Error`: Whisper API エラー
- `UnicodeDecodeError`: 文字エンコーディングエラー

### TDDCog.article_command()

#### 概要
ファイルからMarkdown記事を生成するSlash Command

#### シグネチャ
```python
async def article_command(
    self, 
    interaction: discord.Interaction, 
    file: discord.Attachment, 
    style: str = "prep", 
    include_tldr: bool = False
) -> None
```

#### 入力
- `interaction`: `discord.Interaction` - Discord インタラクションオブジェクト
- `file`: `discord.Attachment` - 処理対象ファイル
- `style`: `str` - 記事スタイル（"prep" | "pas"）
- `include_tldr`: `bool` - TLDR要約の有無

#### 出力
- `None` - 戻り値なし（Discord応答による処理）

#### 処理フロー
1. **即座応答**: `interaction.response.defer()` で3秒ルール対応
2. **重複処理防止**: `RATE_LIMIT_CACHE` でプロセシングフラグ管理
3. **プログレス表示**: 統合Embedでリアルタイム進行状況表示
4. **ユーザー制限チェック**: Premium/無料ユーザー判定
5. **ファイル検証**: MIME タイプ・サイズ・セキュリティチェック
6. **ファイル処理**: 形式別処理（テキスト/PDF/音声/動画）
7. **AI記事生成**: OpenAI GPT-4o-mini で記事作成
8. **TLDR生成**: オプションで要約追加
9. **結果送信**: Markdown ファイル + Embed
10. **メール送信**: fallback ID 対応の Email 送信
11. **モニタリング**: 完了ログとエラー統計

#### Rate Limiting 対策
- **プログレス更新**: embed edit で API 呼び出し削減
- **統合 Email 通知**: 別々のfollowup を embed field に統合
- **エラー処理統一**: 単一 embed でエラー表示

---

## 関数仕様

### 主要ユーティリティ関数

#### check_dependencies()
```python
def check_dependencies() -> None
```
**目的**: システム依存関係の検証
**処理**: FFmpeg, Redis, OpenAI API Key, Discord Token の検証
**例外**: `DependencyError` - 依存関係エラー時

#### safe_discord_api_call()
```python
async def safe_discord_api_call(
    api_call_func: Callable, 
    max_retries: int = 3, 
    base_delay: float = 1.0, 
    user_id: str = None
) -> Any
```
**目的**: Discord API の429エラー対応呼び出し
**入力**: API呼び出し関数、リトライ設定
**出力**: API呼び出し結果またはNone
**処理**: Exponential backoff + Rate Limit ヘッダー解析

#### validate_file_type()
```python
def validate_file_type(filename: str, content: bytes) -> str
```
**目的**: ファイル形式の検証とセキュリティチェック
**入力**: ファイル名、バイナリコンテンツ
**出力**: ファイル形式（"text"|"pdf"|"audio"|"video"）
**例外**: `UnsupportedFileType` - 未対応形式時

#### build_prompt()
```python
def build_prompt(content: str, style: str = "prep") -> str
```
**目的**: AI記事生成用プロンプト構築
**入力**: コンテンツ、スタイル指定
**出力**: 整形されたプロンプト文字列
**テンプレート**: PREP法/PAS法対応

### Rate Limiting 統計関数

#### log_rate_limit_event()
```python
def log_rate_limit_event(user_id: str, command_name: str, error_details: dict) -> None
```
**目的**: 429エラーの統計記録
**処理**: ユーザー別・コマンド別・時間帯別集計

#### get_cached_user_permissions() / set_cached_user_permissions()
```python
def get_cached_user_permissions(user_id: str) -> dict | None
def set_cached_user_permissions(user_id: str, permissions: dict) -> None
```
**目的**: ユーザー権限のキャッシュ管理
**TTL**: 5分間
**効果**: API呼び出し削減

---

## データ構造仕様

### グローバル変数

#### キャッシュシステム
```python
RATE_LIMIT_CACHE = {}  # Rate Limiting 処理状態管理
INSERT_MODE_CACHE = {}  # Insert モード状態管理
EMAIL_HISTORY_CACHE = {}  # メール履歴キャッシュ
USER_PERMISSIONS_CACHE = {}  # ユーザー権限キャッシュ（TTL: 5分）
```

#### Rate Limiting 統計
```python
RATE_LIMIT_STATS = {
    'total_429_errors': int,  # 総429エラー数
    'errors_by_user': dict,   # ユーザー別エラー数
    'errors_by_command': dict,  # コマンド別エラー数
    'errors_by_hour': dict,   # 時間帯別エラー数
    'recent_errors': list     # 直近50件のエラー詳細
}
```

#### 設定定数
```python
BOT_ID = os.getenv("BOT_ID", "default_bot")
CACHE_TTL = 300  # キャッシュ有効期限（5分）
```

### ファイル処理対応形式

| 形式 | 拡張子 | 処理ライブラリ | 最大サイズ |
|------|--------|---------------|-----------|
| テキスト | `.txt`, `.md` | 標準 `decode()` | 10MB |
| PDF | `.pdf` | `pdfminer.six` | 10MB |
| 音声 | `.mp3`, `.wav`, `.m4a`, `.ogg` | OpenAI Whisper | 20MB |
| 動画 | `.mp4`, `.webm` | FFmpeg + Whisper | 20MB |

---

## スラッシュコマンドワークフロー

### 1. /insert コマンドワークフロー

```mermaid
graph TD
    A[/insert 実行] --> B[interaction.response.defer]
    B --> C[重複処理チェック]
    C --> D[処理フラグ設定]
    D --> E[Insert モードキャッシュ登録]
    E --> F[3-6秒ランダム遅延]
    F --> G[完了通知送信]
    G --> H[処理フラグクリア]
    
    I[ユーザーメッセージ] --> J[Insert モードチェック]
    J --> K[Premium/制限チェック]
    K --> L[2-5秒ランダム遅延]
    L --> M[処理通知送信]
    M --> N[OpenAI API 呼び出し]
    N --> O[3-7秒ランダム遅延]
    O --> P[結果ファイル送信]
    P --> Q[メール送信（fallback ID対応）]
```

**特徴:**
- **3段階の遅延**: バースト防止とWAF回避
- **Fallback Email**: `["tdd_bot", "default_bot", "sewasees_bot"]`
- **詳細ログ**: 全プロセスの可視化

### 2. /article コマンドワークフロー

```mermaid
graph TD
    A[/article 実行] --> B[interaction.response.defer]
    B --> C[重複処理防止チェック]
    C --> D[統合プログレスEmbed作成]
    D --> E[初期進行状況送信]
    E --> F[Premium/制限チェック]
    F --> G[ファイル検証]
    G --> H[プログレスEmbed更新: ファイル処理中]
    H --> I[ファイル形式別処理]
    I --> J[プログレスEmbed更新: AI処理中]
    J --> K[AI記事生成]
    K --> L[TLDR生成（オプション）]
    L --> M[結果Embed + ファイル送信]
    M --> N[Email送信（統合表示）]
    N --> O[モデレーターログ]
```

**Rate Limiting対策:**
- **API呼び出し数**: 6-8回 → 2-3回に削減
- **統合プログレス**: 複数followup → 単一embed edit
- **統合Email表示**: 別followup → embed field

### 3. /rate_stats コマンドワークフロー

```mermaid
graph TD
    A[/rate_stats 実行] --> B[管理者権限チェック]
    B --> C[interaction.response.defer]
    C --> D[RATE_LIMIT_STATS 収集]
    D --> E[ユーザー別統計 TOP5]
    E --> F[コマンド別統計]
    F --> G[時間帯別統計 TOP5]
    G --> H[キャッシュ状態表示]
    H --> I[最近のエラー履歴]
    I --> J[統計Embed送信]
```

**出力データ:**
- 429エラー総数・ユーザー別・コマンド別集計
- 時間帯別傾向・キャッシュヒット率
- 直近5件のエラー詳細履歴

---

## 外部サービス統合

### OpenAI API 統合

#### GPT-4o-mini (記事生成)
```python
model="gpt-4o-mini"
max_tokens=2000
temperature=0.7
timeout=30
```

#### Whisper API (音声認識)
```python
model="whisper-1"
language="ja"  # 日本語優先
```

### Email 送信統合

#### SMTP設定
```python
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", 25))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
```

#### Fallback ID システム
```python
fallback_ids = ["tdd_bot", "default_bot", "sewasees_bot"]
```

### Discord API 統合

#### Rate Limiting 対策
- **Exponential Backoff**: 1s → 2s → 4s → 8s
- **詳細ヘッダー解析**: X-RateLimit-*, Retry-After
- **統計収集**: リアルタイム429エラー分析

#### イベント処理
- `on_message`: Insert モード処理
- `on_raw_reaction_add`: 🎤絵文字での音声処理
- `on_command_error`: エラーハンドリング

---

## 技術仕様

### パフォーマンス最適化
- **非同期処理**: asyncio によるノンブロッキングI/O
- **キャッシュシステム**: TTL付きユーザー権限キャッシュ
- **API呼び出し最適化**: 統合Embed、分散タイミング

### セキュリティ
- **ファイル検証**: MIME タイプ + 拡張子チェック
- **実行ファイル拒否**: セキュリティリスク回避
- **レート制限**: ユーザー別日次制限

### 監視・運用
- **詳細ログ**: debug_log_to_file による全操作記録
- **統計収集**: Rate Limiting エラー分析
- **モデレーターログ**: 重要イベントの管理者通知

---

*この仕様書は、TDD Discord Bot v2.0の実装に基づいて作成されています。*
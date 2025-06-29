#!/usr/bin/env python3
"""
TDD Discord Bot - ファイル/音声/動画→Markdown ジェネレータ
仕様書とテストケースに基づいて実装されたDiscord Bot
"""

# --- Additional Imports for Persistent Caching and File Watching ---
import discord
from discord.ext import commands
import asyncio
import os
import tempfile
import hashlib
from datetime import datetime, timezone, timedelta
import json
import subprocess
import mimetypes
from typing import Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv
import logging
import smtplib
from email.message import EmailMessage
import uuid
from pathlib import Path
import yaml
import fcntl
# Persistent cache and file watching support
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Persistent JSON-backed dict for cache ---
class SyncDictJSON(dict):
    _locks = {}
    _instances = {}
    @classmethod
    def create(cls, path):
        lock = cls._locks.setdefault(path, threading.Lock())
        if path not in cls._instances:
            cls._instances[path] = cls(path, lock)
        return cls._instances[path]

    def __init__(self, path, lock):
        super().__init__()
        self.path = path
        self.lock = lock
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        if Path(path).exists():
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            super().update(data)

    def __setitem__(self, key, value):
        with self.lock:
            super().__setitem__(key, value)
            self._flush()

    def __delitem__(self, key):
        with self.lock:
            super().__delitem__(key)
            self._flush()

    def _flush(self):
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self, f, ensure_ascii=False, indent=2)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, self.path)
# --- メール送信ヘルパー ---
async def send_email(recipient: str, subject: str, body: str, attachments: list[tuple[str, bytes, str]] = None):
    """
    Send an email via SMTP.
    attachments: list of (filename, file_bytes, mime_type)
    """
    host = os.getenv("SMTP_HOST", "localhost")
    port = int(os.getenv("SMTP_PORT", 25))
    user = os.getenv("SMTP_USER", "")
    pwd  = os.getenv("SMTP_PASS", "")

    def _sync_send():
        msg = EmailMessage()
        sender = os.getenv("EMAIL_SENDER", user)
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body, subtype="html")
        for fname, data, mime in (attachments or []):
            maintype, subtype = mime.split("/")
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=fname)
        with smtplib.SMTP(host, port) as smtp:
            if user and pwd:
                smtp.starttls()
                smtp.login(user, pwd)
            smtp.send_message(msg)

    await asyncio.to_thread(_sync_send)

# --- ユーザー設定ファイル管理ヘルパー ---
USER_SETTINGS_DIR = Path("data/user_settings")
TEMP_FILES_DIR = Path("temp_files")
BOT_ID = os.getenv("BOT_ID", "default_bot")

# 一時ファイル保存ディレクトリの作成
TEMP_FILES_DIR.mkdir(exist_ok=True)

def load_user_settings(user_id: str) -> dict:
    path = USER_SETTINGS_DIR / f"{user_id}.yaml"
    if not path.exists():
        return {"verified": {}, "pending": {}}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def save_user_settings(user_id: str, data: dict):
    USER_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    path = USER_SETTINGS_DIR / f"{user_id}.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)

def save_temp_file(content: bytes, filename: str, user_id: str) -> str:
    """一時ファイルを保存し、パスを返す（14日間保持）"""
    # ユニークなファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{user_id}_{timestamp}_{filename}"
    temp_path = TEMP_FILES_DIR / unique_filename
    
    # ファイルを保存
    with temp_path.open("wb") as f:
        f.write(content)
    
    return str(temp_path)

def cleanup_old_files():
    """14日以上古い一時ファイルを削除"""
    cutoff_time = datetime.now() - timedelta(days=14)
    
    for file_path in TEMP_FILES_DIR.glob("*"):
        if file_path.is_file():
            # ファイル作成時刻をチェック
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    logger.info(f"Cleaned up old temp file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete old temp file {file_path}: {e}")

# 環境変数読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# INSERT デバッグ用ファイルログ (Discord API負荷なし)
def debug_log_to_file(message: str):
    """DEBUG専用ファイルログ - Discord APIを使わない"""
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("debug_insert.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
            f.flush()
    except Exception as e:
        print(f"Debug log error: {e}")

# --- 依存性チェック ---
class DependencyError(Exception):
    """依存関係エラー"""
    pass

def check_dependencies():
    """必要な依存関係をチェック"""
    errors = []
    
    # ffmpeg チェック
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            errors.append("ffmpeg is not working properly")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        errors.append("ffmpeg is not installed or not in PATH")
    
    # OpenAI API キーチェック
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key or openai_key == 'your_openai_api_key_here':
        errors.append("OPENAI_API_KEY is not set in environment variables")
    
    # Discord Token チェック
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token or discord_token == 'your_discord_bot_token_here':
        errors.append("DISCORD_TOKEN is not set in environment variables")
    
    if errors:
        error_msg = "❌ Dependency check failed:\n" + "\n".join(f"  - {error}" for error in errors)
        logger.warning(error_msg)
        raise DependencyError(error_msg)
    else:
        logger.info("✅ All dependencies check passed")

# --- 例外クラス ---
class UsageLimitExceeded(Exception):
    """使用回数制限超過例外"""
    pass

class UnsupportedFileType(Exception):
    """サポートされていないファイル形式例外"""
    pass

# --- In-memory caches with asyncio locks for thread safety ---
# Fixed: Replace SyncDictJSON with standard dicts + asyncio.Lock to prevent race conditions
RATE_LIMIT_CACHE = SyncDictJSON.create("cache/rate_limit.json")  # Keep for rate limiting
INSERT_MODE_CACHE = {}  # Simple dict with asyncio.Lock protection
insert_cache_lock = None  # Will be initialized in main after event loop starts
# --- Persistent cache for email history (resend_result) ---
EMAIL_HISTORY_CACHE = SyncDictJSON.create("cache/email_history.json")

# --- リミット管理モジュール ---
def limit_user(user_id: str, redis_client=None) -> bool:
    """
    ユーザーの日次使用回数制限をチェック・更新
    """
    use_cache = redis_client is None
    if use_cache:
        cache = RATE_LIMIT_CACHE
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"limit:{user_id}:{today}"
    daily_limit = int(os.getenv('DAILY_RATE_LIMIT', '5'))
    if use_cache:
        count = cache.get(key, 0)
        if count is None:
            count = 0
        if count >= daily_limit:
            raise UsageLimitExceeded(f"1日の使用回数制限（{daily_limit}回）を超過しています")
        cache[key] = count + 1
        return True
    else:
        try:
            current_count = redis_client.get(key)
            if current_count is None:
                current_count = 0
            else:
                current_count = int(current_count)
            if current_count >= daily_limit:
                raise UsageLimitExceeded(f"1日の使用回数制限（{daily_limit}回）を超過しています")
            redis_client.incr(key)
            redis_client.expire(key, 86400)
            return True
        except Exception as e:
            logger.error(f"Redis error: {e}")
            # Redis接続エラーの場合は制限なしで通す（サービス継続のため）
            return True

# --- プロンプト生成モジュール ---
def build_prompt(content: str, style: str = "prep") -> str:
    """
    Markdown記事生成用のプロンプトを構築
    
    Args:
        content: 入力コンテンツ
        style: 記事スタイル ("prep" or "pas")
    
    Returns:
        str: 生成されたプロンプト
    """
    if style == "prep":
        template = """以下のコンテンツを基に、PREP法（Point, Reason, Example, Point）に従って、
構造化されたMarkdown記事を作成してください。

コンテンツ:
{content}

出力形式:
# {{{{POINT}}}}
**要点を明確に述べてください**

## {{{{REASON}}}}
理由や根拠を詳しく説明してください

## {{{{EXAMPLE}}}}
具体例や事例を示してください

## {{{{POINT}}}} (まとめ)
要点を再度強調して結論を述べてください
"""
    else:  # pas style
        template = """以下のコンテンツを基に、PAS法（Problem, Agitation, Solution）に従って、
説得力のあるMarkdown記事を作成してください。

コンテンツ:
{content}

出力形式:
# {{{{POINT}}}}
問題を明確に提示してください

## {{{{REASON}}}}
問題の深刻さや影響を説明してください

## {{{{EXAMPLE}}}}
解決策や提案を具体的に示してください

## {{{{POINT}}}} (まとめ)
解決策の価値を再強調してください
"""
    
    return template.format(content=content)

# --- ファイル処理モジュール ---
async def extract_audio(video_path: str, output_path: str) -> bool:
    """
    動画ファイルから音声を抽出（非同期版）
    
    Args:
        video_path: 入力動画ファイルパス
        output_path: 出力音声ファイルパス
    
    Returns:
        bool: 成功時True
    """
    try:
        cmd = [
            'ffmpeg', '-i', video_path, 
            '-vn', '-ac', '1', '-ar', '16000', 
            '-y', output_path
        ]
        
        # 非同期でsubprocessを実行
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info(f"Audio extraction successful: {video_path} -> {output_path}")
            return True
        else:
            logger.error(f"ffmpeg error: {stderr.decode('utf-8', errors='ignore')}")
            return False
            
    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")
        return False

def validate_file_type(filename: str, content: bytes) -> str:
    """
    ファイル形式の検証
    
    Args:
        filename: ファイル名
        content: ファイルコンテンツ
    
    Returns:
        str: ファイル形式 ("text", "audio", "video", "pdf")
        
    Raises:
        UnsupportedFileType: サポートされていないファイル形式
    """
    mime_type, _ = mimetypes.guess_type(filename)
    ext = os.path.splitext(filename)[1].lower()
    
    # セキュリティチェック: 実行ファイルを拒否
    dangerous_exts = ['.exe', '.bat', '.cmd', '.scr', '.com', '.pif']
    if ext in dangerous_exts:
        raise UnsupportedFileType(f"Unsupported file type: {ext}")
    
    # サポートされている形式をチェック
    text_exts = ['.txt', '.md']
    audio_exts = ['.mp3', '.wav', '.m4a', '.ogg']
    video_exts = ['.mp4', '.webm']
    pdf_exts = ['.pdf']
    
    if ext in text_exts:
        return "text"
    elif ext in audio_exts:
        return "audio" 
    elif ext in video_exts:
        return "video"
    elif ext in pdf_exts:
        return "pdf"
    else:
        raise UnsupportedFileType(f"Unsupported file type: {ext}")

# --- Discord Bot実装 ---
class TDDCog(commands.Cog):
    """TDD BotのスラッシュコマンドCog"""
    def __init__(self, bot):
        self.bot = bot
    @discord.app_commands.command(name="insert", description="次の発言をマークダウン整形します")
    async def insert_command(self, interaction: discord.Interaction):
        """
        /insert スラッシュコマンド: 次の発言をマークダウン整形モードにする
        """
        user_id = str(interaction.user.id)
        processing_key = f"insert_processing:{user_id}"
        
        logger.info(f"INSERT: Starting command for user {user_id}")
        debug_log_to_file(f"INSERT_COMMAND: Starting for user {user_id}")
        
        # Discord標準パターン: 即座にdefer（3秒以内保証）
        try:
            await interaction.response.defer(ephemeral=True)
            debug_log_to_file(f"INSERT_COMMAND: Defer successful for user {user_id}")
        except discord.errors.NotFound:
            logger.error(f"Insert Interaction expired before defer (user: {interaction.user.id})")
            debug_log_to_file(f"INSERT_COMMAND: Interaction expired before defer for user {user_id}")
            return
        except discord.errors.InteractionResponded:
            logger.warning(f"Insert Interaction already responded (user: {interaction.user.id})")
            debug_log_to_file(f"INSERT_COMMAND: Interaction already responded for user {user_id}")
            return
        except Exception as e:
            logger.error(f"Failed to defer Insert interaction: {e}")
            debug_log_to_file(f"INSERT_COMMAND: Failed to defer for user {user_id}: {e}")
            return
        
        # defer成功後にバックグラウンド処理（時間制限なし）
        
        # 重複実行防止チェック
        if processing_key in RATE_LIMIT_CACHE:
            debug_log_to_file(f"INSERT_COMMAND: User {user_id} already processing, rejecting")
            try:
                await interaction.followup.send("⚠️ 既に処理中です。完了をお待ちください。", ephemeral=True)
            except:
                pass  # エラー時は無音
            return
        
        # 処理フラグ設定
        RATE_LIMIT_CACHE[processing_key] = True
        debug_log_to_file(f"INSERT_COMMAND: Set processing flag for user {user_id}")
        
        # キャッシュ書き込み処理
        try:
            from datetime import datetime
            insert_key = f"insert_mode:{user_id}"
            timestamp = datetime.now().isoformat()
            
            debug_log_to_file(f"INSERT_COMMAND: Starting cache write for user {user_id}, key: {insert_key}")
            
            if self.bot.redis_client:
                data = {"style": "md", "timestamp": timestamp}
                self.bot.redis_client.hset(insert_key, mapping=data)
                self.bot.redis_client.expire(insert_key, 300)  # 5分で期限切れ
                debug_log_to_file(f"INSERT_COMMAND: Set Redis cache for user {user_id}, key: {insert_key}")
            else:
                # Use asyncio.Lock to prevent race conditions with INSERT_MODE_CACHE
                async with insert_cache_lock:
                    debug_log_to_file(f"INSERT_COMMAND: Cache before write: {dict(INSERT_MODE_CACHE)}")
                    cache_entry = {"style": "md", "timestamp": timestamp}
                    INSERT_MODE_CACHE[insert_key] = cache_entry
                    # 書き込み後の実際の状態をログ出力
                    actual_entry = INSERT_MODE_CACHE.get(insert_key)
                    debug_log_to_file(f"INSERT_COMMAND: Cache after write - key: {insert_key}, entry: {actual_entry}")
                    debug_log_to_file(f"INSERT_COMMAND: Full cache state: {dict(INSERT_MODE_CACHE)}")
                    debug_log_to_file(f"INSERT_COMMAND: Set local cache for user {user_id}, cache_size: {len(INSERT_MODE_CACHE)}")
            
            debug_log_to_file(f"INSERT_COMMAND: Insert mode activated for user {user_id}")
            
            # Discord標準パターン: followupで完了通知
            try:
                await interaction.followup.send("📝 次の発言をマークダウン整形します", ephemeral=True)
                debug_log_to_file(f"INSERT_COMMAND: Sent followup notification for user {user_id}")
            except Exception as e:
                debug_log_to_file(f"INSERT_COMMAND: Failed to send followup: {e}")
                # followup失敗でも機能は有効
            
            # 成功時のみprocessing_keyをクリア
            try:
                del RATE_LIMIT_CACHE[processing_key]
                debug_log_to_file(f"INSERT_COMMAND: Cleared processing flag for user {user_id}")
            except Exception as e:
                debug_log_to_file(f"INSERT_COMMAND: Failed to clear processing flag: {e}")
                pass
                
        except Exception as e:
            logger.error(f"INSERT: Command error for user {user_id}: {e}")
            debug_log_to_file(f"INSERT_COMMAND: Command error for user {user_id}: {e}")
            # エラー時もprocessing_keyをクリア
            if processing_key in RATE_LIMIT_CACHE:
                del RATE_LIMIT_CACHE[processing_key]
                debug_log_to_file(f"INSERT_COMMAND: Cleared processing flag after error for user {user_id}")
    @discord.app_commands.command(name="help", description="このBotの使い方一覧を表示")
    async def help_command(self, interaction: discord.Interaction):
        try:
            if interaction.response.is_done():
                return
                
            embed = discord.Embed(
                title="📚 Botの使い方",
                description="このBotで使用できるコマンドの一覧です。",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="/article",
                value="📄 ファイル（テキスト、PDF、音声、動画）からMarkdown記事を生成\n"
                      "⚠️ ファイルサイズ制限: 8MB以下\n"
                      "オプション: `style=prep|pas`, `include_tldr=true|false`",
                inline=False
            )
            embed.add_field(
                name="/tldr",
                value="💡 ファイルからTLDR（要約）を生成（テキスト、PDF、音声、動画対応）\n"
                      "⚠️ ファイルサイズ制限: 8MB以下",
                inline=False
            )
            embed.add_field(
                name="/insert",
                value="✍️ /insertエンターキーで待ち受けモードに入ります。 次の入力発言をMarkdown整形します（テキスト入力のみ対応）このコマンドは音声入力によるテキストの整形を前提としています",
                inline=False
            )
            embed.add_field(
                name="🎤 リアクションで文字起こし",
                value="音声・動画ファイルに 🎤 をリアクションでつけると自動で文字起こしします。",
                inline=False
            )
            embed.set_footer(text="開発中: 他にもコマンドを追加予定です！")
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Help command error: {e}")
            # Rate limit防止のため、エラー応答は省略

    @discord.app_commands.choices(
        style=[
            discord.app_commands.Choice(name="PREP 法", value="prep"),
            discord.app_commands.Choice(name="PAS 法", value="pas")
        ]
    )
    @discord.app_commands.command(name="article", description="ファイルからMarkdown記事を生成（8MB以下）")
    @discord.app_commands.describe(
        file="処理したいファイル (テキスト、PDF、音声、動画) ※8MB以下",
        style="記事スタイル (prep または pas)",
        include_tldr="TLDR（要約）も含めて生成する"
    )
    async def article_command(self, interaction: discord.Interaction, file: discord.Attachment, style: str = "prep", include_tldr: bool = False):
        # 最優先: 即座にdefer()を実行
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.error(f"Interaction expired before defer (user: {interaction.user.id})")
            return
        except discord.errors.InteractionResponded:
            logger.warning(f"Interaction already responded (user: {interaction.user.id})")
            return
        except Exception as e:
            logger.error(f"Failed to defer interaction: {e}")
            return
        
        # defer成功後に重複実行防止チェック
        user_id = str(interaction.user.id)
        processing_key = f"processing:{user_id}"
        
        if processing_key in RATE_LIMIT_CACHE:
            try:
                await interaction.followup.send("⚠️ 既に処理中です。完了をお待ちください。", ephemeral=True)
            except:
                pass
            return
            
        # 処理開始フラグ設定
        RATE_LIMIT_CACHE[processing_key] = True
        
        # 処理開始を通知（失敗してもメイン処理は継続）
        try:
            await interaction.followup.send("📝 ファイル処理を開始しています...", ephemeral=True)
        except Exception as e:
            logger.warning(f"Failed to send followup message, continuing: {e}")
            # followup失敗時も処理を継続
        
        try:
            if not self.bot.is_premium_user(interaction.user):
                try:
                    limit_user(str(interaction.user.id), self.bot.redis_client)
                except UsageLimitExceeded as e:
                    embed = discord.Embed(
                        title="使用回数制限",
                        description=str(e),
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
            file_content = await file.read()
            try:
                file_type = validate_file_type(file.filename, file_content)
            except UnsupportedFileType as e:
                embed = discord.Embed(
                    title="サポートされていないファイル形式",
                    description=str(e),
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            # ファイルサイズチェック（ユーザー区分とファイルタイプに応じて）
            if not self.bot.is_premium_user(interaction.user):
                if file_type in ["audio", "video"] and file.size > 20 * 1024 * 1024:
                    embed = discord.Embed(
                        title="Botファイルサイズ制限",
                        description=f"無料ユーザーは音声・動画ファイルは20MB以下のみ対応しています（現在: {file.size / 1024 / 1024:.1f}MB）。\n\n**解決策:**\n• ファイルを圧縮してください\n• Premiumユーザーになると50MBまで処理可能です",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                elif file.size > 10 * 1024 * 1024:
                    embed = discord.Embed(
                        title="Botファイルサイズ制限",
                        description=f"無料ユーザーは10MB以下のファイルのみ処理可能です（現在: {file.size / 1024 / 1024:.1f}MB）。\n\n**解決策:**\n• ファイルを圧縮してください\n• Premiumユーザーになると50MBまで処理可能です",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
            else:
                if file.size > 50 * 1024 * 1024:
                    embed = discord.Embed(
                        title="Botファイルサイズ制限",
                        description=f"Premiumユーザーでも50MBを超えるファイルは処理できません（現在: {file.size / 1024 / 1024:.1f}MB）。\n\n**解決策:**\n• ファイルを圧縮してください\n• より小さなファイルに分割してください",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
            try:
                # ファイル処理進捗通知
                if file_type in ["audio", "video"]:
                    await interaction.followup.send("🎵 音声・動画ファイルを処理中です（時間がかかる場合があります）...", ephemeral=True)
                elif file_type == "pdf":
                    await interaction.followup.send("📄 PDFファイルを処理中です...", ephemeral=True)
                
                if file_type == "text":
                    content = await self.bot.process_text_file(file_content, file.filename)
                elif file_type == "pdf":
                    content = await self.bot.process_pdf_file(file_content)
                elif file_type == "audio":
                    content = await self.bot.process_audio_file(file_content, file.filename)
                elif file_type == "video":
                    content = await self.bot.process_video_file(file_content, file.filename)
                else:
                    raise ValueError(f"Unknown file type: {file_type}")
                
                # AI処理開始通知
                await interaction.followup.send("🤖 AIが記事を生成中です...", ephemeral=True)
                article = await self.bot.generate_article(content, style)
                final_content = article
                if include_tldr:
                    tldr_summary = await self.bot.generate_tldr(content)
                    final_content = f"""# TLDR (要約)\n\n{tldr_summary}\n\n---\n\n{article}"""
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                prefix = "tldr_article" if include_tldr else "article"
                filename = f"{prefix}_{timestamp}.md"
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmp_file:
                    tmp_file.write(final_content)
                    tmp_file.flush()
                    file_obj = discord.File(tmp_file.name, filename=filename)
                    title_text = "記事生成完了 (TLDR付き)" if include_tldr else "記事生成完了"
                    embed = discord.Embed(
                        title=title_text,
                        description=f"ファイル「{file.filename}」から記事を生成しました",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="スタイル", value=style.upper(), inline=True)
                    embed.add_field(name="ファイル形式", value=file_type, inline=True)
                    if include_tldr:
                        embed.add_field(name="📋 TLDR", value="✅ 含む", inline=True)
                    # Send the embed and file, and keep the returned message object
                    sent_msg = await interaction.followup.send(embed=embed, file=file_obj)
                    # --- Send generated article via email ---
                    user_id = str(interaction.user.id)
                    recipient = load_user_settings(user_id).get("verified", {}).get("email", {}).get(BOT_ID)
                    if recipient and recipient != "your_email_recipient_here":
                        subject_email = f"[TDD Bot] Article from {file.filename}"
                        # final_content variable holds the markdown text
                        body_email = final_content.replace("\n", "<br>")
                        # attach the markdown file
                        attachments = [(filename, final_content.encode("utf-8"), "text/markdown")]
                        try:
                            await send_email(recipient, subject_email, body_email, attachments)
                        except Exception as e:
                            logger.error(f"Failed to send email: {e}")
                            try:
                                await interaction.followup.send("⚠️ メール送信に失敗しましたが、記事は正常に生成されました。", ephemeral=True)
                            except:
                                pass  # Rate limit時はサイレント
                    
                        # 一時ファイル保存 (14日間)
                        temp_file_path = save_temp_file(final_content.encode("utf-8"), filename, user_id)
                    
                        # Email history cache saving
                        key = f"last_email:{user_id}:{BOT_ID}"
                        email_data = {
                            "subject": subject_email,
                            "body": body_email,
                            "attachments": json.dumps([{
                                "filename": filename,
                                "path": temp_file_path,
                                "mime_type": "text/markdown"
                            }])
                        }
                        EMAIL_HISTORY_CACHE[key] = email_data
                        
                        try:
                            await interaction.followup.send("📧 記事をメールで送信しました", ephemeral=True)
                        except:
                            pass  # Rate limit時はサイレント
                    else:
                        try:
                            await interaction.followup.send("❌ メール送信先が登録されていません。`/register_email` でメールアドレスを登録してください。", ephemeral=True)
                        except:
                            pass  # Rate limit時はサイレント
                    # --- END PATCH ---
                    await self.bot.log_to_moderator(
                        title="📄 Article Generated",
                        description=f"User {interaction.user.mention} generated article from {file_type} file",
                        color=discord.Color.green(),
                        **{
                            "User ID": interaction.user.id,
                            "File": file.filename,
                            "Size": f"{file.size / 1024:.1f} KB",
                            "Style": style.upper()
                        }
                    )
                    os.unlink(tmp_file.name)
            except asyncio.TimeoutError:
                logger.error("File processing timeout")
                embed = discord.Embed(
                    title="処理タイムアウト",
                    description="ファイルの処理に時間がかかりすぎています。より小さなファイルで再試行してください。",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
            except Exception as e:
                logger.error(f"File processing error: {e}")
                embed = discord.Embed(
                    title="処理エラー",
                    description=f"ファイルの処理中にエラーが発生しました: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                await self.bot.log_to_moderator(
                    title="❌ Processing Error",
                    description=f"Error processing file for user {interaction.user.mention}",
                    color=discord.Color.red(),
                    **{
                        "User ID": interaction.user.id,
                        "File": file.filename,
                        "Error": str(e)[:1000]
                    }
                )
        except Exception as e:
            logger.error(f"Command error: {e}")
            embed = discord.Embed(
                title="エラー",
                description="コマンドの実行中にエラーが発生しました",
                color=discord.Color.red()
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.followup.send(embed=embed)
        finally:
            # 処理完了フラグをクリア
            if processing_key in RATE_LIMIT_CACHE:
                del RATE_LIMIT_CACHE[processing_key]

    @discord.app_commands.command(name="usage", description="本日の使用回数を確認")
    async def usage_command(self, interaction: discord.Interaction):
        if self.bot.is_premium_user(interaction.user):
            embed = discord.Embed(
                title="使用状況",
                description="Premiumユーザーは無制限でご利用いただけます",
                color=discord.Color.gold()
            )
        else:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            key = f"limit:{interaction.user.id}:{today}"
            try:
                if self.bot.redis_client:
                    current_count = self.bot.redis_client.get(key)
                    current_count = int(current_count) if current_count else 0
                else:
                    current_count = 0
                remaining = max(0, self.bot.daily_rate_limit - current_count)
                embed = discord.Embed(
                    title="使用状況",
                    description=f"本日の残り使用回数: {remaining}/{self.bot.daily_rate_limit}回",
                    color=discord.Color.blue()
                )
            except Exception as e:
                logger.error(f"Usage check error: {e}")
                embed = discord.Embed(
                    title="エラー",
                    description="使用状況の確認中にエラーが発生しました",
                    color=discord.Color.red()
                )
        try:
            if interaction.response.is_done():
                return
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Usage command response error: {e}")
            # Rate limit防止のため、エラー応答は省略

    @discord.app_commands.command(name="tldr", description="ファイルから要約（TLDR）を生成（8MB以下）")
    @discord.app_commands.describe(
        file="要約したいファイル (テキスト、PDF、音声、動画) ※8MB以下"
    )
    async def tldr_command(self, interaction: discord.Interaction, file: discord.Attachment):
        # 最優先: 即座にdefer()を実行
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.error(f"TLDR Interaction expired before defer (user: {interaction.user.id})")
            return
        except discord.errors.InteractionResponded:
            logger.warning(f"TLDR Interaction already responded (user: {interaction.user.id})")
            return
        except Exception as e:
            logger.error(f"Failed to defer TLDR interaction: {e}")
            return
        
        # defer成功後に重複実行防止チェック
        user_id = str(interaction.user.id)
        processing_key = f"tldr_processing:{user_id}"
        
        if processing_key in RATE_LIMIT_CACHE:
            try:
                await interaction.followup.send("⚠️ 既にTLDR処理中です。完了をお待ちください。", ephemeral=True)
            except:
                pass
            return
            
        # 処理開始フラグ設定
        RATE_LIMIT_CACHE[processing_key] = True
        try:
            if not self.bot.is_premium_user(interaction.user):
                try:
                    limit_user(str(interaction.user.id), self.bot.redis_client)
                except UsageLimitExceeded as e:
                    embed = discord.Embed(
                        title="使用回数制限",
                        description=str(e),
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
            file_content = await file.read()
            try:
                file_type = validate_file_type(file.filename, file_content)
            except UnsupportedFileType as e:
                embed = discord.Embed(
                    title="サポートされていないファイル形式",
                    description=str(e),
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            # ファイルサイズチェック（ユーザー区分とファイルタイプに応じて）
            if not self.bot.is_premium_user(interaction.user):
                if file_type in ["audio", "video"] and file.size > 20 * 1024 * 1024:
                    embed = discord.Embed(
                        title="ファイルサイズエラー",
                        description="無料ユーザーは音声・動画ファイルは20MB以下のみ対応しています",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                elif file.size > 10 * 1024 * 1024:
                    embed = discord.Embed(
                        title="ファイルサイズエラー",
                        description="無料ユーザーは10MB以下のファイルのみ処理可能です",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
            else:
                if file.size > 50 * 1024 * 1024:
                    embed = discord.Embed(
                        title="ファイルサイズエラー",
                        description="Premiumユーザーでも50MBを超えるファイルは処理できません",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
            try:
                if file_type == "text":
                    content = await self.bot.process_text_file(file_content, file.filename)
                elif file_type == "pdf":
                    content = await self.bot.process_pdf_file(file_content)
                elif file_type == "audio":
                    content = await self.bot.process_audio_file(file_content, file.filename)
                elif file_type == "video":
                    content = await self.bot.process_video_file(file_content, file.filename)
                else:
                    raise ValueError(f"Unknown file type: {file_type}")
                tldr_summary = await self.bot.generate_tldr(content)
                embed = discord.Embed(
                    title="📝 TLDR (要約)",
                    description=tldr_summary,
                    color=discord.Color.blue()
                )
                embed.add_field(name="📁 ファイル", value=file.filename, inline=True)
                embed.add_field(name="📊 形式", value=file_type.upper(), inline=True)
                embed.add_field(name="💾 サイズ", value=f"{file.size / 1024:.1f} KB", inline=True)
                embed.set_footer(text="💡 詳細な記事が必要な場合は /article コマンドをご利用ください")
                sent_msg = await interaction.followup.send(embed=embed)
                # --- Send TLDR via email ---
                user_id = str(interaction.user.id)
                recipient = load_user_settings(user_id).get("verified", {}).get("email", {}).get(BOT_ID)
                if recipient and recipient != "your_email_recipient_here":
                    subject_email = f"[TDD Bot] TLDR from {file.filename}"
                    body_email = tldr_summary.replace("\n", "<br>")
                    try:
                        await send_email(recipient, subject_email, body_email)
                    except Exception as e:
                        logger.error(f"Failed to send TLDR email: {e}")
                        try:
                            await interaction.followup.send("⚠️ メール送信に失敗しましたが、TLDR は正常に生成されました。", ephemeral=True)
                        except:
                            pass  # Rate limit時はサイレント
                
                    # Email history cache saving
                    key = f"last_email:{user_id}:{BOT_ID}"
                    email_data = {
                        "subject": subject_email,
                        "body": body_email,
                        "attachments": "[]"
                    }
                    EMAIL_HISTORY_CACHE[key] = email_data
                    
                    try:
                        await interaction.followup.send("📧 要約をメールで送信しました", ephemeral=True)
                    except:
                        pass  # Rate limit時はサイレント
                else:
                    try:
                        await interaction.followup.send("❌ メール送信先が登録されていません。`/register_email` でメールアドレスを登録してください。", ephemeral=True)
                    except:
                        pass  # Rate limit時はサイレント
                # --- END PATCH ---
                await self.bot.log_to_moderator(
                    title="📋 TLDR Generated",
                    description=f"User {interaction.user.mention} generated TLDR from {file_type} file",
                    color=discord.Color.blue(),
                    **{
                        "User ID": interaction.user.id,
                        "File": file.filename,
                        "Size": f"{file.size / 1024:.1f} KB",
                        "Type": file_type.upper()
                    }
                )
            except Exception as e:
                logger.error(f"TLDR processing error: {e}")
                embed = discord.Embed(
                    title="処理エラー",
                    description=f"ファイルの処理中にエラーが発生しました: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                await self.bot.log_to_moderator(
                    title="❌ TLDR Processing Error",
                    description=f"Error processing TLDR for user {interaction.user.mention}",
                    color=discord.Color.red(),
                    **{
                        "User ID": interaction.user.id,
                        "File": file.filename,
                        "Error": str(e)[:1000]
                    }
                )
        except Exception as e:
            logger.error(f"TLDR command error: {e}")
            embed = discord.Embed(
                title="エラー",
                description="コマンドの実行中にエラーが発生しました",
                color=discord.Color.red()
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.followup.send(embed=embed)
        finally:
            # 処理完了フラグをクリア
            if processing_key in RATE_LIMIT_CACHE:
                del RATE_LIMIT_CACHE[processing_key]

    @discord.app_commands.command(name="register_email", description="メールアドレスを登録し、認証メールを送信します")
    @discord.app_commands.describe(email="登録したいメールアドレス")
    async def register_email(self, interaction: discord.Interaction, email: str):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        settings = load_user_settings(user_id)
        token = uuid.uuid4().hex[:8]
        settings.setdefault("pending", {})[token] = {
            "type": "email",
            "bot_id": BOT_ID,
            "value": email,
            "requested_at": datetime.now(timezone.utc).isoformat()
        }
        save_user_settings(user_id, settings)
        # Build a concise instruction for the user
        body = (
            "メールアドレス認証用トークン:\n"
            f"{token}\n"
            "このトークンをコピーして、Discord 上で `/confirm_email` コマンドを実行して認証を完了してください。\n"
        )
        try:
            await send_email(email, "[TDD Bot] メール認証のお知らせ", body)
            await interaction.followup.send(
                "✅ 認証メールを送信しました。受信ボックスを確認してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Failed to send confirmation email: {e}")
            await interaction.followup.send(
                f"❌ 認証メール送信に失敗しました: {str(e)}",
                ephemeral=True
            )

    @discord.app_commands.command(name="confirm_email", description="認証トークンを入力してメール登録を完了します")
    @discord.app_commands.describe(token="メールに記載の認証トークン")
    async def confirm_email(self, interaction: discord.Interaction, token: str):
        user_id = str(interaction.user.id)
        settings = load_user_settings(user_id)
        entry = settings.get("pending", {}).get(token)
        if not entry:
            await interaction.response.send_message(
                "❌ 無効なトークンです。再度 /register_email を実行してください。",
                ephemeral=True
            )
            return
        settings.setdefault("verified", {}).setdefault("email", {})[entry["bot_id"]] = entry["value"]
        del settings["pending"][token]
        save_user_settings(user_id, settings)
        await interaction.response.send_message(
            "✅ メールアドレスの認証が完了しました。",
            ephemeral=True
        )

    @discord.app_commands.command(name="resend_result", description="直近の生成結果を再度メール送信します")
    async def resend_result(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        key = f"last_email:{user_id}:{BOT_ID}"
        data = EMAIL_HISTORY_CACHE.get(key, {})
        if not data:
            await interaction.followup.send(
                "❌ 再送信可能な送信履歴がありません。",
                ephemeral=True
            )
            return
        subject = data.get("subject")
        body = data.get("body")
        attachments_info = json.loads(data.get("attachments", "[]"))
        recipient = load_user_settings(user_id).get("verified", {}).get("email", {}).get(BOT_ID)
        if not recipient:
            await interaction.followup.send(
                "❌ 登録済みのメールアドレスがありません。 /register_email してください。",
                ephemeral=True
            )
            return

        # 保存済みファイルから添付ファイルを再構築
        attachments = []
        for attachment_info in attachments_info:
            if isinstance(attachment_info, dict) and "path" in attachment_info:
                file_path = Path(attachment_info["path"])
                if file_path.exists():
                    try:
                        with file_path.open("rb") as f:
                            file_content = f.read()
                        attachments.append((
                            attachment_info["filename"],
                            file_content,
                            attachment_info["mime_type"]
                        ))
                    except Exception as e:
                        logger.error(f"Failed to read temp file {file_path}: {e}")

        # メール送信（添付ファイル付き）
        try:
            await send_email(recipient, subject, body, attachments if attachments else None)
        except Exception as e:
            logger.error(f"Failed to resend email: {e}")
            await interaction.followup.send(
                f"❌ メール再送信に失敗しました: {str(e)}",
                ephemeral=True
            )
            return

        attachment_msg = f"（添付ファイル: {len(attachments)}個）" if attachments else "（添付ファイルなし）"
        await interaction.followup.send(
            f"✅ 生成結果を再送信しました。{attachment_msg}",
            ephemeral=True
        )

class TDDBot(commands.Bot):
    """TDD仕様に基づいたDiscord Bot"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        # Cog登録はsetup_hookで行う
        
        # 設定の読み込み
        self.daily_rate_limit = int(os.getenv('DAILY_RATE_LIMIT', '5'))
        self.premium_role_name = os.getenv('PREMIUM_ROLE_NAME', 'premium').lower()
        self.moderator_channel_id = os.getenv('MODERATOR_CHANNEL_ID')
        if self.moderator_channel_id:
            self.moderator_channel_id = int(self.moderator_channel_id)
        
        # OpenAI設定
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # asyncio.Lock for INSERT_MODE_CACHE to prevent race conditions
        global insert_cache_lock
        insert_cache_lock = asyncio.Lock()
        
        # Redis設定: Redisは使用せず、常にNone
        self.redis_client = None
        # insertモード管理用 (Redisベース)
    async def on_message(self, message):
        # CRITICAL: Immediately filter out all bot messages to prevent feedback loops
        if message.author.bot or message.author == self.user:
            return
            
        user_id = str(message.author.id)
        debug_log_to_file(f"ON_MESSAGE: Received message from user {user_id}, content_length: {len(message.content)}")
        insert_mode_entry = None
        
        # INSERT_MODE_CACHE の確認
        if self.redis_client:
            key = f"insert_mode:{user_id}"
            data = self.redis_client.hgetall(key)
            if data:
                insert_mode_entry = {"style": data.get("style", "md"), "timestamp": data.get("timestamp")}
                self.redis_client.delete(key)  # 処理後に削除
                logger.info(f"INSERT: Found Redis insert mode for user {user_id}")
                debug_log_to_file(f"ON_MESSAGE: Found Redis insert mode for user {user_id}, key: {key}")
            else:
                debug_log_to_file(f"ON_MESSAGE: No Redis insert mode for user {user_id}, key: {key}")
        else:
            key = f"insert_mode:{user_id}"
            debug_log_to_file(f"ON_MESSAGE: Checking local cache for user {user_id}, key: {key}")
            
            # Use asyncio.Lock to prevent race conditions with INSERT_MODE_CACHE
            async with insert_cache_lock:
                debug_log_to_file(f"ON_MESSAGE: Cache contents: {dict(INSERT_MODE_CACHE)}")
                debug_log_to_file(f"ON_MESSAGE: Cache size: {len(INSERT_MODE_CACHE)}")
                
                entry = INSERT_MODE_CACHE.get(key)
                if entry:
                    insert_mode_entry = entry
                    logger.info(f"INSERT: Found local insert mode for user {user_id}")
                    debug_log_to_file(f"ON_MESSAGE: Found local insert mode for user {user_id}, entry: {entry}")
                    try:
                        del INSERT_MODE_CACHE[key]
                        debug_log_to_file(f"ON_MESSAGE: Deleted cache entry, remaining cache size: {len(INSERT_MODE_CACHE)}")
                    except Exception as e:
                        logger.error(f"INSERT: Failed to delete cache entry: {e}")
                        debug_log_to_file(f"ON_MESSAGE: Failed to delete cache entry: {e}")
                else:
                    debug_log_to_file(f"ON_MESSAGE: No local insert mode for user {user_id}, key: {key}")
                
        if insert_mode_entry:
            logger.info(f"INSERT: Processing insert for user {user_id}")
            debug_log_to_file(f"ON_MESSAGE: Processing insert for user {user_id}, entry: {insert_mode_entry}")
            
            # UX一貫性: articleと同様の処理開始通知
            try:
                await message.channel.send("📝 マークダウン整形中...", delete_after=30)
                debug_log_to_file(f"ON_MESSAGE: Sent processing notification for user {user_id}")
            except Exception as e:
                debug_log_to_file(f"ON_MESSAGE: Failed to send processing notification: {e}")
                # 通知失敗でも処理は継続
            
            style = insert_mode_entry.get("style", "md")
            prompt = build_prompt(message.content, style)
            
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "あなたはMarkdown整形のエキスパートです。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1200,
                    temperature=0.5,
                    timeout=30
                )
                markdown = response.choices[0].message.content
                logger.info(f"INSERT: OpenAI response received for user {user_id}")
                debug_log_to_file(f"ON_MESSAGE: OpenAI response received for user {user_id}, markdown_length: {len(markdown)}")
                
                # ファイル名生成
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"insert_result_{timestamp}.md"
                
                # 一時ファイル作成とDiscord添付
                import tempfile
                import os
                tmp_file_path = None
                
                try:
                    # 一時ファイル作成
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmp_file:
                        tmp_file.write(markdown)
                        tmp_file.flush()
                        os.fsync(tmp_file.fileno())  # ディスクへの書き込みを確実に実行
                        tmp_file_path = tmp_file.name
                    
                    # ファイルが確実に閉じられた後にDiscordファイルオブジェクト作成
                    file_obj = discord.File(tmp_file_path, filename=filename)
                    
                    # Embedメッセージとファイル添付で送信
                    embed = discord.Embed(
                        title="📝 テキスト整形完了",
                        description="マークダウン形式で整形しました",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="ファイル名", value=filename, inline=True)
                    embed.add_field(name="文字数", value=f"{len(markdown)} 文字", inline=True)
                    
                    sent_msg = await message.channel.send(embed=embed, file=file_obj)
                    debug_log_to_file(f"ON_MESSAGE: Successfully sent file {filename} for user {user_id}")
                    
                    # Discord処理完了を待つ（添付ファイル処理時間を確保）
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    debug_log_to_file(f"ON_MESSAGE: Failed to send file for user {user_id}: {e}")
                    logger.error(f"INSERT: Failed to send markdown file for user {user_id}: {e}")
                    
                finally:
                    # 一時ファイルクリーンアップ（finally節で確実に実行）
                    if tmp_file_path and os.path.exists(tmp_file_path):
                        try:
                            os.unlink(tmp_file_path)
                            debug_log_to_file(f"ON_MESSAGE: Cleaned up temp file for user {user_id}")
                        except Exception as e:
                            debug_log_to_file(f"ON_MESSAGE: Failed to cleanup temp file: {e}")
                
                # --- Send formatted markdown via email with attachment ---
                user_settings = load_user_settings(user_id)
                debug_log_to_file(f"ON_MESSAGE: User settings for {user_id}: {user_settings}")
                debug_log_to_file(f"ON_MESSAGE: BOT_ID being used: {BOT_ID}")
                
                # Email lookup with detailed debugging
                email_dict = user_settings.get("verified", {}).get("email", {})
                debug_log_to_file(f"ON_MESSAGE: Available email keys: {list(email_dict.keys())}")
                recipient = email_dict.get(BOT_ID)
                
                # Fallback: try common bot IDs if primary lookup fails
                if not recipient:
                    for fallback_id in ["tdd_bot", "default_bot", "sewasees_bot"]:
                        if fallback_id in email_dict:
                            recipient = email_dict[fallback_id]
                            debug_log_to_file(f"ON_MESSAGE: Found email with fallback ID {fallback_id}: {recipient}")
                            break
                
                debug_log_to_file(f"ON_MESSAGE: Final email recipient for user {user_id}: {recipient}")
                if recipient:
                    logger.info(f"INSERT: Sending email to {recipient}")
                    
                    # 既に生成されたファイル名を使用
                    subject_email = "[TDD Bot] Insert Result"
                    body_email = markdown.replace("\n", "<br>")
                    attachments = [(filename, markdown.encode("utf-8"), "text/markdown")]
                    
                    try:
                        await send_email(recipient, subject_email, body_email, attachments)
                        logger.info(f"INSERT: Email sent successfully")
                        
                        # 一時ファイル保存 (14日間)
                        temp_file_path = save_temp_file(markdown.encode("utf-8"), filename, user_id)
                        
                        # Email history cache saving
                        key = f"last_email:{user_id}:{BOT_ID}"
                        email_data = {
                            "subject": subject_email,
                            "body": body_email,
                            "attachments": json.dumps([{
                                "filename": filename,
                                "path": temp_file_path,
                                "mime_type": "text/markdown"
                            }])
                        }
                        EMAIL_HISTORY_CACHE[key] = email_data
                        
                        await message.channel.send("📧 整形結果をメールで送信しました（添付ファイル付き）", delete_after=30)
                        
                    except Exception as e:
                        logger.error(f"INSERT: Failed to send email: {e}")
                        debug_log_to_file(f"ON_MESSAGE: Failed to send email: {e}")
                        await message.channel.send("⚠️ メール送信に失敗しましたが、整形は正常に完了しました。", delete_after=30)
                else:
                    # ユーザーがメール未登録の場合の処理
                    debug_log_to_file(f"ON_MESSAGE: No email recipient for user {user_id}")
                    await message.channel.send("❌ メール送信先が登録されていません。`/register_email` でメールアドレスを登録してください。", delete_after=30)
                    
            except Exception as e:
                logger.error(f"INSERT: Failed to process insert: {e}")
                debug_log_to_file(f"ON_MESSAGE: Failed to process insert for user {user_id}: {e}")
                try:
                    await message.channel.send("❌ テキスト整形中にエラーが発生しました。", delete_after=30)
                except:
                    pass  # Prevent cascading errors during rate limiting
        else:
            debug_log_to_file(f"ON_MESSAGE: No insert mode entry found for user {user_id}")
        
        # Process commands
        try:
            await self.process_commands(message)
        except Exception as e:
            debug_log_to_file(f"ON_MESSAGE: Failed to process commands: {e}")
            pass  # Prevent cascading errors during rate limiting
    
    async def on_ready(self):
        """Bot 起動時処理（接続確認＋モデレーターログのみ）"""
        logger.info(f'{self.user} has connected to Discord!')
        
        # ユーザー設定ディレクトリの状況をログ出力
        debug_log_to_file(f"BOT_STARTUP: Checking user settings directory: {USER_SETTINGS_DIR}")
        if USER_SETTINGS_DIR.exists():
            user_files = list(USER_SETTINGS_DIR.glob("*.yaml"))
            debug_log_to_file(f"BOT_STARTUP: Found {len(user_files)} user settings files")
            for user_file in user_files:
                debug_log_to_file(f"BOT_STARTUP: User file: {user_file.name}")
        else:
            debug_log_to_file(f"BOT_STARTUP: User settings directory does not exist")

        # Note: FileWatcher removed - INSERT_MODE_CACHE is now in-memory dict with asyncio.Lock

        # 古い一時ファイルのクリーンアップ
        cleanup_old_files()

        await self.log_to_moderator(
            title="🤖 Bot Started",
            description="Bot has connected successfully.",
            color=discord.Color.green()
        )
    
    async def log_to_moderator(self, title: str, description: str, color: discord.Color = discord.Color.blue(), **kwargs):
        """モデレーターチャンネルにログを送信"""
        if not self.moderator_channel_id:
            return
        
        try:
            channel = self.get_channel(self.moderator_channel_id)
            if channel:
                embed = discord.Embed(title=title, description=description, color=color)
                embed.timestamp = datetime.now(timezone.utc)
                
                # 追加フィールドがあれば追加
                for field_name, field_value in kwargs.items():
                    embed.add_field(name=field_name, value=str(field_value), inline=True)
                
                await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send moderator log: {e}")
    
    def is_premium_user(self, member: discord.Member) -> bool:
        """Premiumユーザーかどうかを判定"""
        # テスト用: 全ユーザーをPremiumとして扱う
        # 本番環境では下記の元のコードに戻すこと
        return True
        
        # 元のコード（本番用）:
        # if not member.roles:
        #     return False
        # return any(role.name.lower() == self.premium_role_name for role in member.roles)
    
    async def process_text_file(self, content: bytes, filename: str) -> str:
        """テキストファイルの処理"""
        try:
            text = content.decode('utf-8')
            return text
        except UnicodeDecodeError:
            # UTF-8で読めない場合は他のエンコーディングを試す
            for encoding in ['cp932', 'shift_jis', 'iso-2022-jp']:
                try:
                    text = content.decode(encoding)
                    return text
                except UnicodeDecodeError:
                    continue
            raise ValueError("Could not decode text file")
    
    async def process_pdf_file(self, content: bytes) -> str:
        """PDFファイルの処理"""
        try:
            from pdfminer.high_level import extract_text
            import io
            
            # バイトコンテンツからテキストを抽出
            text = extract_text(io.BytesIO(content))
            
            if not text.strip():
                raise ValueError("PDF appears to be empty or contains no extractable text")
            
            # 長すぎるテキストは制限
            max_length = 8000  # GPT-4o-miniのトークン制限を考慮
            if len(text) > max_length:
                text = text[:max_length] + "\n\n[テキストが長すぎるため切り詰められました]"
            
            return text.strip()
            
        except ImportError:
            raise ValueError("pdfminer.six is not installed. Please install it with: pip install pdfminer.six")
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            raise ValueError(f"PDFの処理中にエラーが発生しました: {str(e)}")
    
    async def process_audio_file(self, content: bytes, filename: str) -> str:
        """音声ファイルの処理"""
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()

            def sync_transcribe(path):
                client = OpenAI(timeout=60)  # Whisper API用に60秒タイムアウト
                with open(path, 'rb') as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                return transcript.text

            try:
                return await asyncio.to_thread(sync_transcribe, tmp_file.name)
            finally:
                os.unlink(tmp_file.name)
    
    async def process_video_file(self, content: bytes, filename: str) -> str:
        """動画ファイルの処理"""
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as video_file:
            video_file.write(content)
            video_file.flush()
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as audio_file:
                try:
                    # 動画から音声を抽出（非同期）
                    success = await extract_audio(video_file.name, audio_file.name)
                    if not success:
                        raise ValueError("Failed to extract audio from video")

                    # 抽出した音声をテキストに変換 (openai>=1.0.0)
                    def sync_transcribe(path):
                        client = OpenAI(timeout=60)  # Whisper API用に60秒タイムアウト
                        with open(path, 'rb') as af:
                            transcript = client.audio.transcriptions.create(
                                model="whisper-1",
                                file=af
                            )
                        return transcript.text

                    return await asyncio.to_thread(sync_transcribe, audio_file.name)
                finally:
                    os.unlink(video_file.name)
                    os.unlink(audio_file.name)
    
    async def generate_tldr(self, content: str) -> str:
        """長文コンテンツのTLDR（要約）を生成"""
        # 長すぎるコンテンツは制限
        if len(content) > 6000:
            content = content[:6000] + "...[要約のため一部省略]"
        
        prompt = f"""以下のコンテンツを読みやすい要約（TLDR形式）にしてください。

要求事項：
- 3〜5つの要点を箇条書きで
- 各ポイントは絵文字付きで分かりやすく
- 全体で200文字以内
- 読者がすぐに理解できる簡潔さ

コンテンツ:
{content}

出力形式:
🔹 [要点1]
🔹 [要点2]
🔹 [要点3]
"""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは要約のエキスパートです。長文を短く分かりやすい要点にまとめることに特化しています。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3,  # 要約は一貫性を重視
            timeout=30  # 30秒タイムアウト
        )

        return response.choices[0].message.content

    async def generate_article(self, content: str, style: str = "prep") -> str:
        """OpenAI GPT-4o-miniを使用してMarkdown記事を生成"""
        prompt = build_prompt(content, style)

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは優秀なライターです。与えられたコンテンツから構造化されたMarkdown記事を作成してください。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,
            timeout=30  # 30秒タイムアウト
        )

        return response.choices[0].message.content
    
    async def on_raw_reaction_add(self, payload):
        """🎤/❤️ リアクションで音声・動画処理 or ツイートプレビュー"""
        # Ignore reaction updates/removals – handle only actual ADD events
        if getattr(payload, "event_type", "REACTION_ADD") != "REACTION_ADD":
            return
        # --- Heart Reaction for Tweet Preview ---
        if str(payload.emoji) == "❤️":
            # Only respond to heart reactions added to messages sent by this bot
            if payload.user_id == self.user.id:
                return
            try:
                channel = self.get_channel(payload.channel_id)
                if channel is None:
                    return
                message = await channel.fetch_message(payload.message_id)
                if message.author.id != self.user.id:
                    return
                # Try to extract the original content to tweet
                tweet_content = None
                import re
                # Priority: If the message has a markdown code block, extract it
                codeblock_match = re.search(r"```markdown\n(.+?)\n```", message.content, re.DOTALL)
                if codeblock_match:
                    tweet_content = codeblock_match.group(1)
                # New: If the message has an embed (article generation), try to extract preview from referenced message/.md file
                elif message.embeds:
                    for embed in message.embeds:
                        if embed.description and "から記事を生成しました" in embed.description:
                            # Try to find referenced Markdown file text content
                            if message.reference:
                                try:
                                    ref_msg = await channel.fetch_message(message.reference.message_id)
                                    if ref_msg.attachments:
                                        md_file = ref_msg.attachments[0]
                                        if md_file.filename.endswith(".md"):
                                            md_bytes = await md_file.read()
                                            md_text = md_bytes.decode('utf-8', errors='ignore')
                                            tweet_content = md_text[:600]
                                            break
                                except Exception as e:
                                    logger.warning(f"Failed to fetch .md content from referenced message: {e}")
                # Fallback: message.content (if not already handled)
                elif message.content:
                    tweet_content = message.content
                # Final fallback: try to extract content from .md file directly
                if not tweet_content and message.attachments:
                    for attachment in message.attachments:
                        if attachment.filename.endswith(".md"):
                            try:
                                md_bytes = await attachment.read()
                                md_text = md_bytes.decode('utf-8', errors='ignore')
                                tweet_content = md_text[:600]
                                break
                            except Exception as e:
                                logger.warning(f"Failed to read .md file content for tweet: {e}")
                # Truncate/summarize to 140 chars, but use LLM if needed
                if tweet_content:
                    preview = tweet_content.replace('\n', ' ').replace('　', ' ')
                    if len(preview) > 140:
                        # Use the new prompt allowing emoji for tweet summary
                        original_content = tweet_content
                        response = self.openai_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "あなたはプロのSNSライターです。魅力的でインパクトのあるツイートを作成します。"},
                                {"role": "user", "content": f"以下の内容を140文字以内で魅力的なツイートにしてください。適切な絵文字を使っても構いません。\n\n{original_content}"}
                            ],
                            max_tokens=160,
                            temperature=0.7
                        )
                        candidate = response.choices[0].message.content.strip().replace('\n', ' ')
                        logger.info(f"🧪 Candidate tweet: {candidate} ({len(candidate)} chars)")
                        if len(candidate) <= 140:
                            preview = candidate
                        else:
                            preview = candidate[:140]
                else:
                    preview = "(内容を取得できません)"
                # Build the Twitter intent URL
                from urllib.parse import quote
                intent_url = f"https://twitter.com/intent/tweet?text={quote(preview[:140])}"
                # Log preview and URL
                if tweet_content:
                    logger.info(f"✅ Final tweet preview: {preview} ({len(preview)} chars)")
                    logger.info(f"🌐 Tweet intent URL: {intent_url} ({len(intent_url)} chars)")

                # --- Modal edit UI for tweet before sending ---
                from discord.ui import Modal, TextInput, View
                import discord

                class TweetModal(Modal):
                    def __init__(self, preview_text: str):
                        super().__init__(title="ツイートを編集")
                        self.tweet = TextInput(
                            label="ツイート内容（140字以内）",
                            style=discord.TextStyle.paragraph,
                            default=preview_text,
                            max_length=140
                        )
                        self.add_item(self.tweet)

                    async def on_submit(self, interaction: discord.Interaction):
                        final_tweet = self.tweet.value
                        tweet_url = f"https://twitter.com/intent/tweet?text={quote(final_tweet)}"
                        # self.stop()  # Close the modal properly
                        await interaction.response.send_message(
                            f"✅ ツイートはこちらから投稿できます:\n{tweet_url}",
                            ephemeral=True
                        )

                # 追加: TweetActionView
                class TweetActionView(View):
                    def __init__(self, preview_text):
                        super().__init__(timeout=120)
                        self.preview_text = preview_text

                    @discord.ui.button(label="✏️ 編集", style=discord.ButtonStyle.primary)
                    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        modal = TweetModal(preview_text=self.preview_text)
                        await interaction.response.send_modal(modal)

                    @discord.ui.button(label="🚀 投稿", style=discord.ButtonStyle.success)
                    async def post_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        tweet_url = f"https://twitter.com/intent/tweet?text={quote(self.preview_text)}"
                        await interaction.response.send_message(f"✅ ツイートはこちらから投稿できます:\n{tweet_url}", ephemeral=True)

                # TextChannel: show tweet preview and action buttons
                if isinstance(channel, discord.TextChannel):
                    await channel.send(
                        content=f"✍️ ツイートプレビューが生成されました。以下が内容です。\n```{preview[:140]}```",
                        view=TweetActionView(preview[:140])
                    )
                # DMChannel or Thread: show preview and link
                elif isinstance(channel, discord.DMChannel) or isinstance(channel, discord.Thread):
                    tweet_url = intent_url
                    await channel.send(f"📝 編集後のツイート:\n```{preview[:140]}```\n[ツイート画面を開く]({tweet_url})")
                else:
                    tweet_url = intent_url
                    await channel.send(f"📝 編集後のツイート:\n```{preview[:140]}```\n{tweet_url}")
                return
            except Exception as e:
                logger.error(f"Heart reaction tweet preview error: {e}")
            return
        # --- 🎤 Reaction for transcription (original logic) ---
        if str(payload.emoji) not in ["🎤", "🎙️"]:
            return
        if payload.user_id == self.user.id:
            return
        try:
            channel = self.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            # 添付ファイルがあるかチェック
            if not message.attachments:
                return
            for attachment in message.attachments:
                try:
                    file_type = validate_file_type(attachment.filename, b'')
                    if file_type not in ["audio", "video"]:
                        continue
                    # 使用回数制限チェック（Premium以外）
                    user = self.get_user(payload.user_id)
                    if hasattr(user, 'roles'):  # ギルドメンバーの場合
                        guild = self.get_guild(payload.guild_id)
                        member = guild.get_member(payload.user_id)
                        if not self.is_premium_user(member):
                            limit_user(str(payload.user_id), self.redis_client)
                    # 文字起こしログ
                    await self.log_to_moderator(
                        title="🎤 Transcription Request",
                        description=f"User {user.mention if user else f'<@{payload.user_id}>'} requested transcription via reaction",
                        color=discord.Color.blue(),
                        **{
                            "User ID": payload.user_id,
                            "File": attachment.filename,
                            "Type": file_type
                        }
                    )
                    # ファイル処理
                    file_content = await attachment.read()
                    if file_type == "audio":
                        content = await self.process_audio_file(file_content, attachment.filename)
                    else:  # video
                        content = await self.process_video_file(file_content, attachment.filename)
                    # 文字起こし結果をファイルとして保存・送信
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"transcript_{timestamp}.txt"
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
                        tmp_file.write(content)
                        tmp_file.flush()
                        file_obj = discord.File(tmp_file.name, filename=filename)
                        embed = discord.Embed(
                            title="文字起こし完了",
                            description=f"「{attachment.filename}」の文字起こしが完了しました",
                            color=discord.Color.green()
                        )
                        await channel.send(embed=embed, file=file_obj)
                        os.unlink(tmp_file.name)
                except Exception as e:
                    logger.error(f"Reaction processing error: {e}")
                    await channel.send("処理中にエラーが発生しました")
        except Exception as e:
            logger.error(f"Reaction handler error: {e}")

    async def setup_hook(self):
        """Cog 登録と Slash コマンド同期を確実に実行する"""
        # 1) Cog を登録
        await self.add_cog(TDDCog(self))
        
        # デバッグ: 登録されたコマンドを確認
        logger.info(f"Commands in tree: {[cmd.name for cmd in self.tree.get_commands()]}")

        # 2) Slash コマンド同期
        try:
            # グローバル同期を試す
            synced = await self.tree.sync()
            logger.info(f"[setup_hook] Synced {len(synced)} global command(s)")
            for cmd in synced:
                logger.info(f"  - {cmd.name}")
        except Exception as e:
            logger.error(f"[setup_hook] Failed to sync commands: {e}")

        # 3) テスト用コマンド
        @self.command(name="ping")
        async def ping(ctx):
            await ctx.send("Pong!")

# --- プロセスロック機能 ---
def acquire_lock():
    """プロセスロックを取得して複数インスタンス起動を防ぐ"""
    lock_file_path = "/tmp/tdd_bot.lock"
    try:
        lock_file = open(lock_file_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        logger.info("✅ Process lock acquired successfully")
        return lock_file
    except IOError:
        logger.error("❌ Another instance of TDD Bot is already running")
        return None

# --- メイン実行部 ---
def main():
    """メイン実行関数"""
    # プロセスロック取得
    lock_file = acquire_lock()
    if not lock_file:
        return 1
    
    try:
        # 依存性チェック
        try:
            check_dependencies()
        except DependencyError as e:
            logger.error(e)
            return 1
        
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            logger.error("DISCORD_TOKEN environment variable is required")
            return 1
        
        bot = TDDBot()
        
        try:
            bot.run(token)
        except Exception as e:
            logger.error(f"Bot failed to start: {e}")
            return 1
            
    finally:
        # プロセス終了時にロックファイルを解放
        if lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            try:
                os.unlink("/tmp/tdd_bot.lock")
            except:
                pass
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
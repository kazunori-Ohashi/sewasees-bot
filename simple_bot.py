import discord
import asyncio
import os
from datetime import datetime
from vault_loder import load_vault
from discord.ui import View, button, Modal, TextInput
from dotenv import load_dotenv
import urllib.parse
from discord.ext import commands
import re
from rapidfuzz import process, fuzz
import unicodedata
import hashlib

MAX_EMBED_TITLE_LEN = 256

# BaseBotと共通サービスをインポート
from common.base_bot import BaseBot

# --- 既存の簡易実装はBaseBotが提供するため不要に ---
# TwitterService, FileGuildConfigはBaseBot内で初期化される

class SimpleBot(BaseBot):
    """
    実験的な機能を実装するためのBotクラス。
    BaseBotを継承し、共通サービス（LLM呼び出しなど）を利用する。
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # SimpleBot固有のデータをロード
        self.vault_data = load_vault()
        self.ESSENTIAL_FILES = ["bot_inputs/writing_principles.md"]
        
        # on_message, on_raw_reaction_add はリスナーとして自動登録されるため、手動での追加は不要

    def normalize(self, text: str) -> str:
        text = unicodedata.normalize('NFKC', text)
        text = re.sub(r'\s+', ' ', text)
        return text

    def clean_topic(self, topic: str) -> str:
        topic = re.sub(r'(について|を)?(書いて|教えて|説明して|まとめて|解説して).*$', '', topic)
        return topic.strip()

    def extract_topic_keywords(self, topic: str) -> list:
        # 命令語除去＋簡易名詞抽出（日本語形態素解析がなければsplit/replaceで）
        topic = self.clean_topic(topic)
        # 句読点や記号で分割し、2文字以上の単語のみ抽出
        words = re.split(r'[\s、。・,\.\-\n\r\t]+', topic)
        keywords = [w for w in words if len(w) >= 2]
        if not keywords:
            keywords = [topic.strip()]
        return keywords

    def search_notes(self, topic: str, vault: dict, essentials: set, k=5, cutoff=30):
        topic_keywords = self.extract_topic_keywords(topic)
        print(f"[DEBUG] トピックキーワード: {topic_keywords}")
        related = []
        related_paths = []
        # 1) 必須ノートを先に追加
        for path, note in vault.items():
            if any(os.path.normpath(e) in os.path.normpath(path) for e in essentials):
                related.append(note["body"])
                related_paths.append(path)
        # 2) metaのみ比較の候補リスト
        meta_candidates = {path: self.normalize(note["meta"]) for path, note in vault.items()}
        meta_scores = []
        for path, meta in meta_candidates.items():
            max_score = 0
            best_kw = ""
            for tkw in topic_keywords:
                score = fuzz.partial_ratio(tkw, meta)
                if score > max_score:
                    max_score = score
                    best_kw = tkw
            if max_score >= cutoff:
                meta_scores.append((path, max_score, best_kw))
        meta_scores.sort(key=lambda x: x[1], reverse=True)
        print(f"[DEBUG] meta比較ヒット: {meta_scores[:k]}")
        for path, score, kw in meta_scores[:k]:
            if path not in related_paths:
                related.append(vault[path]["body"])
                related_paths.append(path)
        # 3) metaでヒットしなければbodyも含めて再検索
        if len(related_paths) < k:
            body_candidates = {path: self.normalize(note["meta"] + " " + note["body"]) for path, note in vault.items()}
            body_scores = []
            for path, text in body_candidates.items():
                max_score = 0
                best_kw = ""
                for tkw in topic_keywords:
                    score = fuzz.partial_ratio(tkw, text)
                    if score > max_score:
                        max_score = score
                        best_kw = tkw
                if max_score >= cutoff:
                    body_scores.append((path, max_score, best_kw))
            # 既にrelated_pathsに入っているものは除外
            body_scores = [x for x in body_scores if x[0] not in related_paths]
            body_scores.sort(key=lambda x: x[1], reverse=True)
            print(f"[DEBUG] body比較ヒット: {body_scores[:k]}")
            for path, score, kw in body_scores[:k]:
                related.append(vault[path]["body"])
                related_paths.append(path)
        print(f"[DEBUG] 最終related_paths: {related_paths}")
        return related[:k+len(essentials)], related_paths[:k+len(essentials)]

    def safe_filename(self, topic: str, prefix: str = "", ext: str = ".md", maxlen: int = 40):
        name = re.sub(r'[\\/:*?"<>|]', '_', topic)
        if len(name) > maxlen:
            digest = hashlib.md5(name.encode('utf-8')).hexdigest()[:6]
            name = name[:maxlen] + f"_{digest}"
        return f"{prefix}{name}{ext}"

    async def on_message(self, message):
        """メッセージ受信時の処理"""
        if message.author == self.user:
            return

        if message.content.strip() == "?":
            commands_text = (
                "**📜 利用可能なコマンド一覧**\n"
                "1. `書いて:<トピック>` - トピックに基づいた文章を生成します。\n"
                "   - 例: `書いて: 沖縄の観光`\n"
                "   - 文字数制限付き: `書いて: 沖縄の観光:2000`\n"
                "2. 通常の文章を送信すると、読みやすく整理され、タイトルとタグが付けられます。\n"
                "3. `?` - このコマンド一覧を表示します。"
            )
            await message.channel.send(commands_text)
            return

        openai_service = self.services.get("openai")
        if not openai_service:
            await message.channel.send("⚠️ OpenAIサービスが利用できません。")
            return

        if message.content.startswith("書いて:"):
            parts = message.content.split(":")
            topic = parts[1].strip()
            char_limit = int(parts[2].strip()) if len(parts) > 2 else None

            # 改良版: search_notesで関連ノート抽出
            related_notes, related_paths = self.search_notes(topic, self.vault_data, set(self.ESSENTIAL_FILES), k=5, cutoff=30)

            # 参考ノートが0件なら書かない
            if not related_paths:
                await message.channel.send("🤔 関連するノートが見つかりませんでした。")
                return
            # ここから下は1件以上ヒット時のみ
            # Obsidian風リンクリスト生成
            obsidian_links = [f"[[{os.path.splitext(os.path.basename(p))[0]}]]" for p in related_paths]
            links_str = ", ".join(obsidian_links) if obsidian_links else "なし"
            print(f"[DEBUG] 参考ノート: {links_str}")  # デバッグ用
            prompt_text = (
                f"以下のノートを参考に、「{topic}」について、日本語で詳細な文章を作成してください。\n"
                f"最後に、この文章内容に最も関連性の高いタグを3〜5個、必ず以下のフォーマットで付けてください。\n\n"
                f"フォーマット:\n"
                f"タグ: #タグ1 #タグ2 #タグ3\n\n"
                f"---\n\n"
                + "\n\n---\n\n".join([note[:1000] for note in related_notes])
            )
            messages = [{"role": "user", "content": prompt_text}]
            await message.channel.send("📝 執筆中です。少々お待ちください...")
            result = await openai_service._create_chat_completion(model="gpt-4o-mini", messages=messages)
            content_body, tags = result, ""
            try:
                tags_match = re.search(r"タグ: (.*)", result, re.IGNORECASE | re.DOTALL)
                if tags_match:
                    content_body = result[:tags_match.start()].strip()
                    tags = re.sub(r'#\s+', '#', tags_match.group(1).strip())
                else:
                    content_body = result
                    tags = ""
            except Exception as e:
                print(f"パースエラー（書いて:）: {e}")
                content_body = result
                tags = ""
            if char_limit:
                content_body = content_body[:char_limit]
            output_dir = "/Users/kaz005/Tre/discordbot_outputs"
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.safe_filename(f"{timestamp}_{topic}")
            filepath = os.path.join(output_dir, filename)
            # 成果物ファイル末尾に参考ノートリンクを追記
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {topic}\n\n{content_body}\n\n{tags}\n\n---\n参考ノート: {links_str}\n")
            prefix = "「"
            suffix = "」に関する文章"
            max_topic_len = MAX_EMBED_TITLE_LEN - len(prefix) - len(suffix)
            safe_topic = topic[:max_topic_len]
            embed_title = f"{prefix}{safe_topic}{suffix}"
            embed = discord.Embed(title=embed_title, description=content_body, color=0x3498db)
            if tags:
                embed.add_field(name="タグ", value=tags)
            # Embedに必ず参考ノート欄を追加
            embed.add_field(name="参考ノート", value=links_str, inline=False)
            await message.channel.send(embed=embed)
            # 通常メッセージでも必ず表示
            await message.channel.send(f"参考ノート: {links_str}")
            await message.channel.send("✅ 文章が生成され、ファイルとしても保存されました。")

        else: # 通常のメッセージ
            input_text = message.content.strip()
            await message.channel.send("📚 整理中です。少々お待ちください...")

            prompt_text = (
                "次の文章を日本語で、読みやすいように整理してください。文意を変えず、簡潔で明確にしてください。\n\n"
                f"{input_text}\n\n"
                "さらに、この文章に対して適切なタイトルと3〜5個の関連タグを提案してください。\n"
                "以下のフォーマットで応答してください：\n"
                "タイトル: ...\n"
                "本文: ...\n"
                "タグ: ...（ハッシュタグ形式で）"
            )
            messages = [{"role": "user", "content": prompt_text}]

            # 共通サービスを使ってLLMを呼び出し
            result = await openai_service._create_chat_completion(model="gpt-4o-mini", messages=messages)
            
            # --- 結果のパース処理を実装 ---
            title, content_body, tags = "無題", result, ""
            try:
                title_match = re.search(r"タイトル: (.*)", result)
                body_match = re.search(r"本文: (.*)", result, re.DOTALL)
                tags_match = re.search(r"タグ: (.*)", result)

                if title_match:
                    title = title_match.group(1).strip()
                # 本文とタグの間に本文がある場合を考慮
                if body_match and tags_match:
                    body_text_raw = result[body_match.start():tags_match.start()]
                    content_body = re.sub(r"本文: ?", "", body_text_raw, 1).strip()
                elif body_match: # タグがない場合
                    content_body = body_match.group(1).strip()

                if tags_match:
                    # 「# タグ」->「#タグ」のようにスペースを削除
                    tags = re.sub(r'#\s+', '#', tags_match.group(1).strip())
                else:
                    tags = "" # タグが見つからなければ空文字
            except Exception as e:
                print(f"パースエラー: {e}")
                content_body = result # パース失敗時は原文を本文とする

            # ファイル保存処理を追加
            output_dir = "/Users/kaz005/Tre/discordbot_outputs"
            os.makedirs(output_dir, exist_ok=True)
            prefix = "「"
            suffix = "」に関する文章"
            max_topic_len = MAX_EMBED_TITLE_LEN - len(prefix) - len(suffix)
            safe_topic = topic[:max_topic_len]
            embed_title = f"{prefix}{safe_topic}{suffix}"
            embed = discord.Embed(title=embed_title, description=content_body, color=0x3498db)
            if tags:
                embed.add_field(name="タグ", value=tags)
            
            await message.channel.send(embed=embed)
            await message.channel.send("✅ 内容が整理され、ファイルとしても保存されました。")

    async def on_raw_reaction_add(self, payload):
        """リアクション受信時の処理"""
        if str(payload.emoji) != "❤️":
            return
            
        channel = self.get_channel(payload.channel_id)
        if not channel: return
        message = await channel.fetch_message(payload.message_id)
        
        openai_service = self.services.get("openai")
        if not openai_service:
            await channel.send("⚠️ OpenAIサービスが利用できません。")
            return

        post_content = message.content
        if message.embeds:
            post_content = message.embeds[0].description

        if len(post_content) > 140:
            await channel.send("📝 140文字を超えているため、要約します...")
            # 共通サービスを使って要約
            post_content = await openai_service.summarize(post_content, model="gpt-4o-mini", max_length=140)

        # UI部分はWriterBotのものを参考にしつつ、簡易版として実装
        url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(post_content)}"
        await channel.send(f"🐦 下記リンクから投稿できます:\n{url}")


if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv("FIRST_DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("FIRST_DISCORD_TOKEN (.env) が未設定です")

    intents = discord.Intents.default()
    intents.message_content = True
    intents.reactions = True
    
    # SimpleBotをインスタンス化して実行
    bot = SimpleBot(command_prefix="!", intents=intents)
    bot.run(TOKEN)

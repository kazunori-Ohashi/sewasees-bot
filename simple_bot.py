import discord
import asyncio  # この行を追加
import os
from datetime import datetime
from generate import generate_with_gemma
from vault_loder import load_vault
from discord.ui import View, button, Button
from dotenv import load_dotenv

# --- TwitterService簡易実装 ---
import tweepy
class TwitterService:
    def __init__(self):
        self.client = tweepy.Client(
            consumer_key=os.getenv("TW_API_KEY"),
            consumer_secret=os.getenv("TW_API_SECRET"),
            access_token=os.getenv("TW_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TW_ACCESS_SECRET"),
        )
    def post(self, text: str):
        return self.client.create_tweet(text=text)

# --- guild_config層 ---
import json
class FileGuildConfig:
    def __init__(self, config_dir: str = ".guild_config"):
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)
    def _get_path(self, guild_id: int) -> str:
        return os.path.join(self.config_dir, f"{guild_id}.json")
    def get_plan(self, guild_id: int) -> str:
        path = self._get_path(guild_id)
        if not os.path.exists(path):
            return "free"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("PLAN", "free")

# Discord Botのトークン
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

ESSENTIAL_FILES = ["bot_inputs/writing_principles.md"]

# Vaultを読み込む
vault_data = load_vault()

guild_config = FileGuildConfig()

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True
intents.members = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ ログインしました: {client.user}")
    
class TwitterPostView(View):
    def __init__(self, content, guild_id):
        super().__init__()
        self.content = content
        self.guild_id = guild_id

    @button(label="Xに投稿（本体）", style=discord.ButtonStyle.primary)
    async def post_main(self, interaction, button):
        plan = guild_config.get_plan(self.guild_id)
        if plan != "pro":
            embed = discord.Embed(
                title="有料プラン限定機能",
                description="X（Twitter）投稿はProプランでご利用いただけます。\n/upgrade コマンドで詳細をご確認ください。",
                color=0xffd700
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        tw = TwitterService()
        try:
            resp = tw.post(self.content)
            await interaction.response.send_message(
                f"✅ 投稿完了: https://x.com/i/web/status/{resp.data['id']}", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"⚠️ 投稿失敗: {e}", ephemeral=True
            )

    @button(label="投稿内容を編集", style=discord.ButtonStyle.secondary)
    async def edit_post(self, interaction, button):
        await interaction.response.send_message("✏️ 編集モードは現在未対応です。", ephemeral=True)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.strip() == "?":
        commands = (
            "**📜 利用可能なコマンド一覧**\n"
            "1. `書いて:<トピック>` - トピックに基づいた文章を生成します。\n"
            "   - 例: `書いて: 沖縄の観光`\n"
            "   - 文字数制限付き: `書いて: 沖縄の観光:2000`\n"
            "2. 通常の文章を送信すると、読みやすく整理され、タイトルとタグが付けられます。\n"
            "3. `?` - このコマンド一覧を表示します。"
        )
        await message.channel.send(commands)
        return

    if message.content.startswith("書いて:"):
        parts = message.content.split(":")
        topic = parts[1].strip()
        char_limit = int(parts[2].strip()) if len(parts) > 2 else None

        related = []
        for path, content in vault_data.items():
            if any(essential in path for essential in ESSENTIAL_FILES):
                related.append((path, content))
        for path, content in vault_data.items():
            if topic.lower() in content.lower() and (path, content) not in related:
                related.append((path, content))

        if related:
            # 修正後
            prompt = (
                f"以下のノートを参考に、「{topic}」について、"
                f"日本語で文章を作成してください。\n\n"
            )
            for _, content in related:
                prompt += content[:1000] + "\n\n"

            await message.channel.send("📝 執筆中です。少々お待ちください...")

            result = await asyncio.to_thread(generate_with_gemma, prompt)

            if char_limit:
                result = result[:char_limit]

            # 保存処理
            output_dir = "/Users/kaz005/Tre/discordbot_outputs"
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{topic}.md"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {topic}\n\n{result}")
                # 関連ノートのリンクを追加
                related_paths = [path for path, _ in related]
                if related_paths:
                    f.write("\n\n## 関連ノート\n")
                    for path in related_paths:
                        filename_only = os.path.splitext(os.path.basename(path))[0]
                        f.write(f"- [[{filename_only}]]\n")

            await message.channel.send("✅ 文章が生成され、ファイルとして保存されました。Vaultでご確認ください。")
        else:
            await message.channel.send("🤔 関連するノートが見つかりませんでした。")

    else:
        input_text = message.content.strip()

        await message.channel.send("📚 整理中です。少々お待ちください...")

        related = []
        for path, content in vault_data.items():
            if any(word in content for word in input_text.split()):
                related.append(path)

        prompt = (
            "次の文章を日本語で、読みやすいように整理してください。文意を変えず、簡潔で明確にしてください。\n\n"
            f"{input_text}\n\n"
            "さらに、この文章に対して適切なタイトルと3〜5個の関連タグを提案してください。\n"
            "以下のフォーマットで応答してください：\n"
            "タイトル: ...\n"
            "本文: ...\n"
            "タグ: ...（ハッシュタグ形式で）"
        )

        result = await asyncio.to_thread(generate_with_gemma, prompt)

        # 結果を分解して title、content、tags に分ける
        title, content_body, tags = "無題", "", ""
        if "タイトル:" in result and "本文:" in result and "タグ:" in result:
            try:
                title_part = result.split("タイトル:")[1]
                content_part = title_part.split("本文:")[1]
                tag_part = content_part.split("タグ:")
                title = title_part.split("本文:")[0].strip()
                content_body = tag_part[0].strip()
                tags = tag_part[1].strip()
            except Exception:
                content_body = result.strip()
        else:
            content_body = result.strip()

        # 保存処理
        output_dir = "/Users/kaz005/Tre/discordbot_outputs"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in "_- ").rstrip()
        filename = f"{timestamp}_{safe_title}.md"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            formatted_tags = "\n".join(f"# {tag.strip('#').strip()}" for tag in tags.split() if tag.strip())
            f.write(f"# {title}\n\n{content_body}\n\n## タグ\n{formatted_tags}")
            if related:
                f.write("\n\n## 関連ノート\n")
                for path in related:
                    filename_only = os.path.splitext(os.path.basename(path))[0]
                    f.write(f"- [[{filename_only}]]\n")

        # 関連ノート探索
        related_note_list = "\n".join(f"- {path}" for path in related) if related else "関連するノートは見つかりませんでした。"

        # Discord送信用の整理結果表示
        summary = (
            f"✅ 整理結果\n\n"
            f"**タイトル**: {title}\n\n"
            f"**本文**:\n{content_body}\n\n"
            f"**タグ**:\n{tags}\n\n"
            f"**関連ノート**:\n{related_note_list}"
        )
        if related:
            link_section = "\n".join(f"- [[{os.path.splitext(os.path.basename(path))[0]}]]" for path in related)
            summary += f"\n\n**関連ノートへのリンク**:\n{link_section}"
        await message.channel.send(summary[:2000])

@client.event
async def on_raw_reaction_add(payload):
    if str(payload.emoji.name) == "❤️":
        channel = client.get_channel(payload.channel_id)
        if channel is None:
            return
        message = await channel.fetch_message(payload.message_id)
        user = payload.member
        if user is not None and not user.bot:
            guild_id = message.guild.id if message.guild else None
            view = TwitterPostView(message.content, guild_id)
            preview = message.content[:2000]
            try:
                await channel.send(
                    f"この内容をX（Twitter）に投稿しますか？\n\n{preview}",
                    view=view
                )
            except discord.HTTPException as e:
                await channel.send("⚠️ 投稿準備メッセージの送信に失敗しました。内容が長すぎる可能性があります。")

client.run(TOKEN)

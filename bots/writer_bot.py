# bots/writer_bot.py
from common.base_bot import BaseBot
from discord.ext import commands
import discord
from dotenv import load_dotenv
from io import BytesIO
from common.services.twitter import TwitterService
from discord import ui
from common.services.auth import PaymentServiceV2

class WriterBot(BaseBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register()

    def register(self):
        @self.command(name="write")
        async def write(ctx, *, topic: str):
            if not await self.has_access(ctx.author, "write"):
                await ctx.send("🚫 この機能は有料プランです。")
                return
            # ここに GPT 呼び出しロジック
            await ctx.send(f"『{topic}』について執筆中…")

        @self.command(name="tweet")
        async def tweet(ctx, *, text: str):
            if not await self.has_access(ctx.author, "twitter_post"):
                await ctx.send("🔒 有料機能やで")
                return
            tw = self.services["twitter"]
            resp = tw.post(text)
            await ctx.send(f"🐦 投稿完了: https://x.com/i/web/status/{resp.data['id']}")

        @self.command(name="transcribe")
        async def transcribe(ctx):
            if not await self.has_access(ctx.author, "transcribe"):
                await ctx.send("🔒 有料機能やで")
                return
            if not ctx.message.attachments:
                await ctx.send("音声ファイルを添付してください")
                return
            file = ctx.message.attachments[0]
            file_path = f"/tmp/{file.filename}"
            await file.save(file_path)
            whisper = self.services["whisper"]
            text = await whisper.transcribe(file_path)
            await ctx.send(f"文字起こし結果: {text}")

        @self.command(name="invite")
        async def invite(ctx):
            embed = discord.Embed(title="Botをサーバーに招待", description="下記リンクからBotを追加できます。", color=0x00bfff)
            embed.add_field(name="招待リンク", value="[Botを招待](https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot&permissions=8)")
            await ctx.send(embed=embed)

        @self.command(name="upgrade")
        async def upgrade(ctx):
            embed = discord.Embed(title="プラン比較・アップグレード", color=0xffd700)
            embed.add_field(name="Free", value="・基本コマンド\n・一部機能制限", inline=True)
            embed.add_field(name="Pro", value="・全機能解放\n・Bot名/アイコン自由\n・サポート付き", inline=True)
            embed.add_field(name="詳細・申込", value="[アップグレードはこちら](https://your-landing-page.example.com)", inline=False)
            await ctx.send(embed=embed)

        @self.command(name="clean")
        async def clean(ctx, *, text: str):
            """入力テキストをMarkdown整形し、ファイル添付で返す"""
            if not await self.has_access(ctx.author, "clean"):
                return await ctx.send("🔒 有料機能です")
            # 1. LLM呼び出し (モデルを指定)
            md = await self.services["openai"].to_markdown(text, model="gpt-4o-mini")
            # 2. BytesIOへ書き込み
            buf = BytesIO(md.encode("utf-8"))
            buf.seek(0)
            # 3. 添付ファイル作成
            discord_file = discord.File(buf, filename="cleaned.md")
            # 4. 送信（案内文＋整形済みテキスト＋ファイル添付）
            content = f"✅ 整形完了！Markdown をダウンロードしてね。\n\n{md}"
            await ctx.send(
                content=content,
                file=discord_file
            )

        @self.command(name="set_paid")
        async def set_paid(ctx):
            payment = self.services["payment"]
            payment.set_paid(ctx.author.id)
            await ctx.send("✅ あなたを有料ユーザーに設定しました。")

        @self.command(name="set_free")
        async def set_free(ctx):
            payment = self.services["payment"]
            payment.set_free(ctx.author.id)
            await ctx.send("✅ あなたを無料ユーザーに設定しました。")

        @self.command(name="my_plan")
        async def my_plan(ctx):
            payment = self.services["payment"]
            is_paid = payment.is_paid(ctx.author.id)
            plan = "有料ユーザー (Pro)" if is_paid else "無料ユーザー (Free)"
            await ctx.send(f"あなたの現在のプラン: {plan}")

if __name__ == "__main__":
    import os
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN (.env) が未設定です")
    intents = discord.Intents.default()
    intents.message_content = True
    intents.reactions = True
    bot = WriterBot(command_prefix="/", intents=intents)

    class TweetConfirmView(ui.View):
        def __init__(self, original_content, author_id):
            super().__init__(timeout=180)
            self.content = original_content
            self.author_id = author_id
            self.tweet_result = None

        @ui.button(label="Xに投稿", style=discord.ButtonStyle.primary)
        async def tweet_button(self, interaction: discord.Interaction, button: ui.Button):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("他の人は操作できません", ephemeral=True)
                return
            if not await interaction.client.has_access(interaction.user, "twitter_post"):
                await interaction.response.send_message(
                    "🔒 この機能は有料プラン限定です。\n/upgrade コマンドで詳細をご確認ください。",
                    ephemeral=True
                )
                return
            tw = TwitterService()
            url = tw.create_intent_url(self.content)
            await interaction.response.send_message(
                f"🐦 下記リンクからX（Twitter）投稿画面を開けます:\n<{url}>",
                ephemeral=True
            )
            self.tweet_result = url
            self.stop()
            # 投稿完了後にUIメッセージを削除
            await interaction.message.delete()

        @ui.button(label="投稿内容を編集", style=discord.ButtonStyle.secondary)
        async def edit_button(self, interaction: discord.Interaction, button: ui.Button):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("他の人は操作できません", ephemeral=True)
                return
            modal = TweetEditModal(self.content)
            await interaction.response.send_modal(modal)
            await modal.wait()
            if modal.new_content:
                self.content = modal.new_content
                # 編集後はすべてのUIを消し、X投稿リンクだけをephemeralで返す
                tw = TwitterService()
                url = tw.create_intent_url(self.content)
                await interaction.followup.send(
                    f"🐦 下記リンクからX（Twitter）投稿画面を開けます:\n<{url}>",
                    ephemeral=True
                )
                # 編集画面・元UIを削除
                try:
                    await interaction.message.delete()
                except Exception:
                    pass

    class TweetEditModal(ui.Modal, title="投稿内容を編集"):
        new_content: str = None
        def __init__(self, current_content):
            super().__init__()
            self.input = ui.TextInput(label="投稿内容", style=discord.TextStyle.paragraph, default=current_content, max_length=280)
            self.add_item(self.input)
        async def on_submit(self, interaction: discord.Interaction):
            self.new_content = self.input.value
            # メッセージ送信を削除（X投稿リンクのみ表示されるように）
            self.stop()

    @bot.event
    async def on_raw_reaction_add(payload):
        print("[DEBUG] on_raw_reaction_add発火: emoji=", payload.emoji.name, "user=", payload.user_id, "message_id=", payload.message_id)
        if str(payload.emoji.name) == "❤️":
            channel = bot.get_channel(payload.channel_id)
            if channel is None:
                print("[DEBUG] チャンネル取得失敗")
                return
            try:
                message = await channel.fetch_message(payload.message_id)
                print("[DEBUG] message取得:", message.content)
                print(f"[DEBUG] message.embeds: {message.embeds}")
                if message.embeds and getattr(message.embeds[0], 'description', None):
                    print(f"[DEBUG] Embed description: {message.embeds[0].description}")
                else:
                    print(f"[DEBUG] message.content: {message.content}")
                # まずEmbedのdescriptionを優先
                post_content = None
                if message.embeds and getattr(message.embeds[0], 'description', None):
                    post_content = message.embeds[0].description.strip()
                else:
                    # 案内文・説明文など不要な定型文を除外
                    content_lines = message.content.splitlines()
                    exclude_phrases = [
                        "内容を編集してから投稿もできます",
                        "整形完了！Markdown をダウンロードしてね。",
                        "内容を編集してから投稿もできます",
                        "この内容をそのままXに投稿しますか？",
                        "X投稿内容の確認",
                        "---",
                        "このMarkdown形式で、文章がより構造化され、読みやすくなりました。",
                    ]
                    filtered_lines = [line for line in content_lines if line.strip() and all(phrase not in line for phrase in exclude_phrases)]
                    post_content = "\n".join(filtered_lines).strip()
                    # 案内文しか残らない場合は直前のユーザー発言を取得
                    if not post_content:
                        history = [m async for m in channel.history(limit=10, before=message)]
                        user_message = next((m for m in history if not m.author.bot), None)
                        if user_message:
                            post_content = user_message.content.strip()
                        else:
                            post_content = message.content.strip()  # 万一見つからなければ元のcontent
                print(f"[DEBUG] post_content(before summarize): {post_content}")
                # 140文字を超えている場合はLLMで要約
                if len(post_content) > 140:
                    print(f"[DEBUG] 投稿内容が140文字を超えています（{len(post_content)}文字）。LLMで要約します。")
                    openai_service = getattr(bot, 'services', {}).get("openai")
                    if openai_service:
                        try:
                            # モデルを指定して要約
                            post_content = await openai_service.summarize(post_content, model="gpt-4o-mini", max_length=140)
                        except Exception as e:
                            print(f"[ERROR] LLM要約失敗: {e}")
                    # 140文字超過時の警告はUI側で表示
                print(f"[DEBUG] post_content(after summarize): {post_content}")
                if not post_content:
                    post_content = "⚠️ 投稿内容が空です"
                # 140文字超過時は赤文字警告＋Embed色も赤
                if len(post_content) > 140:
                    warning = f"**⚠️ この投稿内容は140文字を超えています（{len(post_content)}文字）**\n"
                    embed = discord.Embed(description=warning + post_content, color=0xff0000)
                else:
                    embed = discord.Embed(description=post_content, color=0x1da1f2)
                view = TweetConfirmView(post_content, payload.user_id)
                await channel.send(content=f"<@{payload.user_id}> 投稿内容を確認してください", embed=embed, view=view)
                print("[DEBUG] Embed+View送信完了")
            except Exception as e:
                print("[ERROR] on_raw_reaction_add例外:", e)
                await channel.send(f"⚠️ エラー: {e}")

    bot.run(TOKEN)
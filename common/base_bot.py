# common/base_bot.py
import os, logging
from discord.ext import commands
from common.auth import is_premium
from common.ratelimit import RateLimiter
from common.feature_flag import FeatureFlagManager
from common.services.whisper import WhisperService
from common.services.twitter import TwitterService
from common.guild_config import FileGuildConfig
from common.services.openai_api import OpenAIService
from common.services.auth import PaymentService, PaymentServiceV2

class BaseBot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cfg = FeatureFlagManager("config.yml")
        self.rate_limiter = RateLimiter(db_path="rate.db")
        self.guild_config = FileGuildConfig()
        self.payment_v2 = PaymentServiceV2()
        self.add_listener(self.on_ready)
        # ▼サービスをひとまとめにして子ボットへ渡す
        self.services = {
            "whisper": WhisperService(),
            "twitter": TwitterService(),
            "openai": OpenAIService(),
            "payment": self.payment_v2,
        }

    async def on_ready(self):
        print(f"✅ Logged in as {self.user}")

    # --- 共通ユーティリティ ------------------------
    async def has_access(self, member, feature: str) -> bool:
        guild_id = getattr(member.guild, "id", None)
        plan = self.guild_config.get_plan(guild_id) if guild_id else "free"
        # 例: pro限定機能はfreeならFalse
        if feature in ["twitter_post", "transcribe"]:
            if self.payment_v2.is_paid(member.id):
                return True
            if plan == "pro":
                return True
            return False
        if not self.cfg.is_enabled(feature):
            return False
        if self.cfg.is_premium_only(feature) and not is_premium(member):
            return False
        return await self.rate_limiter.check(member.id, feature)

    # 子クラス側に「コマンド登録」だけさせる
    def register(self):
        raise NotImplementedError
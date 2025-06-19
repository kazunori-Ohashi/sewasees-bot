import os
import json
from typing import Optional

class GuildConfigBase:
    def get_plan(self, guild_id: int) -> str:
        raise NotImplementedError
    def set_plan(self, guild_id: int, plan: str):
        raise NotImplementedError

class FileGuildConfig(GuildConfigBase):
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

    def set_plan(self, guild_id: int, plan: str):
        path = self._get_path(guild_id)
        data = {"PLAN": plan}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2) 
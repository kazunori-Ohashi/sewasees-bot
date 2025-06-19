# 認証系サービスの骨格
class AuthService:
    def __init__(self):
        pass 

import os
import json
from typing import Optional

class PaymentService:
    """
    課金・プラン管理サービス。将来的なStripe/Patreon等の外部連携や、
    ユーザー情報（名前・住所等）の管理もここに集約する。
    """
    def __init__(self, db_path: str = ".payment_db.json"):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load(self):
        with open(self.db_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def set_paid(self, user_id: int, info: Optional[dict] = None):
        """ユーザーを有料化し、必要なら追加情報も保存"""
        data = self._load()
        data[str(user_id)] = {"paid": True, "info": info or {}}
        self._save(data)

    def set_free(self, user_id: int):
        """ユーザーを無料化"""
        data = self._load()
        data[str(user_id)] = {"paid": False, "info": {}}
        self._save(data)

    def is_paid(self, user_id: int) -> bool:
        data = self._load()
        return data.get(str(user_id), {}).get("paid", False)

    def get_info(self, user_id: int) -> dict:
        data = self._load()
        return data.get(str(user_id), {}).get("info", {})

    # 今後: Stripe/Patreon連携、決済履歴、ユーザー情報入力UIなどもここに追加 

class PaymentServiceV2:
    """
    DiscordユーザーIDごとに data/user_data/{id}.json を作成し、有料/無料状態を管理
    """
    def __init__(self, user_data_dir: str = "data/user_data"):
        self.user_data_dir = user_data_dir
        os.makedirs(self.user_data_dir, exist_ok=True)

    def _get_path(self, user_id: int) -> str:
        return os.path.join(self.user_data_dir, f"{user_id}.json")

    def set_paid(self, user_id: int, info: Optional[dict] = None):
        path = self._get_path(user_id)
        data = {"paid": True, "info": info or {}}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def set_free(self, user_id: int):
        path = self._get_path(user_id)
        data = {"paid": False, "info": {}}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def is_paid(self, user_id: int) -> bool:
        path = self._get_path(user_id)
        print(f"[DEBUG] is_paid: user_id={user_id} path={path}")
        if not os.path.exists(path):
            print("[DEBUG] is_paid: ファイルが存在しません → False")
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = data.get("paid", False)
        print(f"[DEBUG] is_paid: ファイル内容={data} → result={result}")
        return result

    def get_info(self, user_id: int) -> dict:
        path = self._get_path(user_id)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("info", {}) 
# ダミー実装: すべて許可

class RateLimiter:
    def __init__(self, db_path=None):
        pass

    async def check(self, member_id, feature):
        return True 
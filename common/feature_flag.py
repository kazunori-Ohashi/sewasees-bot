# ダミー実装: すべて有効・プレミアム判定はFalse

class FeatureFlagManager:
    def __init__(self, config_path=None):
        pass

    def is_enabled(self, feature):
        return True

    def is_premium_only(self, feature):
        return False 
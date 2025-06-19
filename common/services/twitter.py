import urllib.parse

class TwitterService:
    def __init__(self, handle: str = None):
        self.handle = handle or ""

    def create_intent_url(self, text: str, tags: list[str] = None) -> str:
        """
        投稿用web intent URLを生成
        :param text: 投稿本文
        :param tags: ハッシュタグ（リスト）
        :return: intent URL
        """
        base_url = "https://twitter.com/intent/tweet"
        params = {
            "text": text,
        }
        if tags:
            params["hashtags"] = ",".join([t.lstrip("#") for t in tags])
        if self.handle:
            params["via"] = self.handle.lstrip("@")
        query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        return f"{base_url}?{query}" 
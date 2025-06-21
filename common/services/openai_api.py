# OpenAI API 共通呼び出しサービスの骨格
import aiohttp
import os

class OpenAIService:
    """
    OpenAIのAPIと通信するためのサービスクラス。
    各メソッドでモデルを指定できるため、Botごとに最適なモデルを使い分けることが可能。
    """
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
        if not self.api_key:
            print("⚠️ 警告: OPENAI_API_KEYが設定されていません。OpenAI関連機能は使用できません。")

    async def _create_chat_completion(self, model: str, messages: list[dict], max_tokens: int = 2048) -> str | None:
        """
        OpenAIのChat Completions APIを叩く共通メソッド。
        """
        if not self.api_key:
            return "エラー: OpenAI APIキーが設定されていません。"

        endpoint = "/chat/completions"
        url = self.base_url + endpoint
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ OpenAI APIエラー: {response.status} {error_text}")
                        return f"APIエラーが発生しました (コード: {response.status})。"
                    
                    data = await response.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"❌ 予期せぬエラー: {e}")
            return "予期せぬエラーが発生しました。"

    async def to_markdown(self, text: str, model: str) -> str:
        """指定されたモデルを使い、テキストをMarkdown形式に整形する。"""
        messages = [
            {"role": "system", "content": "あなたはテキスト整形のエキスパートです。"},
            {"role": "user", "content": (
                "次の文章を日本語で、読みやすいMarkdown形式に整形してください。\n"
                "・箇条書きや見出しを適切に使い、構造化してください。\n"
                "・文意を変えずに、元の文章の内容を維持してください。\n\n"
                f"--- START ---\n{text}\n--- END ---"
            )}
        ]
        return await self._create_chat_completion(model=model, messages=messages)

    async def summarize(self, text: str, model: str, max_length: int = 140) -> str:
        """指定されたモデルを使い、テキストをmax_length文字以内に要約する。"""
        messages = [
             {"role": "system", "content": "あなたは文章要約のエキスパートです。"},
             {"role": "user", "content": f"以下の文章を、必ず日本語で、{max_length}文字以内に要約してください。\n\n--- START ---\n{text}\n--- END ---"}
        ]
        # トークン数はおおよその目安
        return await self._create_chat_completion(model=model, messages=messages, max_tokens=int(max_length * 1.5)) 
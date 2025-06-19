# OpenAI API 共通呼び出しサービスの骨格
import aiohttp
import os

# generate_with_gemmaをこのファイル内にコピー
from ollama import Client
client = Client(host='http://localhost:11434')  # デフォルトポート

def generate_with_gemma(prompt: str) -> str:
    response = client.chat(model='gemma3:4b', messages=[
        {"role": "user", "content": prompt}
    ])
    return response['message']['content']

class OpenAIService:
    def __init__(self, api_url: str = None):
        self.api_url = api_url or os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")

    async def to_markdown(self, text: str) -> str:
        prompt = (
            "次の文章を日本語で、読みやすいMarkdown形式に整形してください。\n"
            "・箇条書きや見出しを適切に使い、構造化してください。\n"
            "・本文はそのまま、文意を変えずに整理してください。\n"
            f"\n{text}\n"
        )
        # generate_with_gemmaは同期関数なのでスレッドで実行
        import asyncio
        loop = asyncio.get_event_loop()
        md = await loop.run_in_executor(None, generate_with_gemma, prompt)
        return md 

    async def summarize(self, text: str, max_length: int = 140) -> str:
        """
        LLM（ollama等）でtextをmax_length文字以内に要約する。
        最大5回までリトライし、最後に得られた要約文（140文字超でも）をそのまま返す。
        警告文は返さず、UI側で赤文字警告を付与する設計。
        """
        prompt = f"必ず日本語で、{max_length}文字以内で要約してください。\n{text}"
        result = ""
        for i in range(5):
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "gemma3:4b",
                    "prompt": prompt,
                    "stream": False
                }
                async with session.post(self.api_url, json=payload) as resp:
                    js = await resp.json()
                    print(f"[DEBUG] LLM API response: {js}")
                    result = js.get("response", "")
                    if result and len(result) <= max_length:
                        return result
                    # 空や超過なら再要約
                    prompt = f"もう一度、必ず{max_length}文字以内で日本語で要約してください。\n{result or text}"
        return result or text 
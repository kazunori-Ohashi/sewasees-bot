import aiohttp
import os

class WhisperService:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    async def transcribe(self, file_path: str, lang: str = "ja"):
        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = aiohttp.FormData()
        data.add_field("model", "whisper-1")
        data.add_field("file", open(file_path, "rb"), filename="audio.mp3")
        async with aiohttp.ClientSession() as sess, sess.post(url, headers=headers, data=data) as r:
            js = await r.json()
            return js["text"] 
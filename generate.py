from ollama import Client

client = Client(host='http://localhost:11434')  # デフォルトポート

def generate_with_gemma(prompt: str) -> str:
    response = client.chat(model='gemma3:4b', messages=[
        {"role": "user", "content": prompt}
    ])
    return response['message']['content']
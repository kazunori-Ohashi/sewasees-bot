import os

VAULT_PATH = "/Users/kaz005/Tre"

def load_vault() -> dict:
    knowledge = {}
    for root, _, files in os.walk(VAULT_PATH):
        for file in files:
            if file.endswith(".md"):
                full_path = os.path.join(root, file)
                with open(full_path, "r", encoding="utf-8") as f:
                    knowledge[full_path] = f.read()
    return knowledge
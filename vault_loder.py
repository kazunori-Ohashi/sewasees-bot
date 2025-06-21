import os
import yaml
import unicodedata
import re

def safe_join(val):
    if isinstance(val, list):
        return " ".join([str(x) for x in val])
    return str(val) if val is not None else ""

VAULT_PATH = "/Users/kaz005/Tre"

def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def load_vault() -> dict:
    knowledge = {}
    for root, _, files in os.walk(VAULT_PATH):
        for file in files:
            if file.endswith(".md"):
                full_path = os.path.normpath(os.path.join(root, file))
                with open(full_path, "r", encoding="utf-8") as f:
                    text = f.read()
                fm = {}
                body = text
                if text.startswith("---"):
                    try:
                        _, front, body = text.split("---", 2)
                        fm = yaml.safe_load(front) or {}
                    except Exception:
                        fm = {}
                        body = text
                meta = " ".join([
                    os.path.splitext(file)[0],
                    safe_join(fm.get("aliases", [])),
                    safe_join(fm.get("tags", []))
                ])
                knowledge[full_path] = {
                    "body": body,
                    "meta": meta
                }
    return knowledge
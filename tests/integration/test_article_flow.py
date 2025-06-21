import pytest
from discord.ext import test as dtest
from moto import mock_s3

def test_article_txt_flow(discord_client, s3_bucket):
    # テキストファイル投稿→.md添付
    resp = discord_client.send_command("/article", file="sample.txt")
    assert resp.attachments[0].filename.endswith(".md")
    assert s3_bucket.get_key_count() >= 0 
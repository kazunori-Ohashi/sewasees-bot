import pytest
from mybot.api import article_endpoint

def test_unsupported_extension(client):
    resp = client.post('/article', files={'file': ('malware.exe', b'fake', 'application/octet-stream')})
    assert resp.status_code == 415 
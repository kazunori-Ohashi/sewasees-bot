import pytest
import fakeredis
from moto import mock_s3
import httpx

@pytest.fixture
def redis_client():
    r = fakeredis.FakeStrictRedis()
    yield r
    r.flushall()

@pytest.fixture(scope='function')
def s3_bucket():
    with mock_s3():
        # S3バケットセットアップ
        yield ...

@pytest.fixture
def client():
    # FastAPI/Flask等のテストクライアント返却
    yield ... 
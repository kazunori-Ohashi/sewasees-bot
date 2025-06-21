# フリー版 Discord Bot テスト仕様書（TDD完全版）

---

## 1. テスト範囲と前提

### 1.1 テスト対象
| レイヤ         | 主なモジュール・関数                       |
|----------------|--------------------------------------------|
| ユニット       | limit_user(), extract_audio(), build_prompt()|
| インテグレーション | Discord Slash/リアクション一連フロー・S3連携 |
| システム       | 并列12msg/秒ロードに対する応答率            |
| セキュリティ   | MIME/拡張子検証・権限昇格防止              |

### 1.2 制約・基準
- ファイルサイズ制限 : 無料ユーザーはデフォルト25MB（本文では10MB上限）
- 音声抽出 : ffmpeg -i in.mp4 -vn -ac 1 -ar 16000 out.wav
- Whisper 料金 : $0.006/分
- GPT-4o-mini 料金 : in 0.15$/Mtok / out 0.60$/Mtok
- Redisモック : fakeredis本家ドキュメント準拠

---

## 2. テストケース詳細
| ID      | 種別   | 事前状態                | 手順                | 期待結果                                 |
|---------|--------|------------------------|---------------------|------------------------------------------|
| UT-001  | Logic  | limit_userキー値4      | 関数呼出            | 戻り値True, Redis値5                     |
| UT-002  | Logic  | キー値5                | 同上                | UsageLimitExceeded例外                   |
| UT-003  | I/O    | sample.mp4 10MB        | extract_audio       | output.wav存在                           |
| UT-004  | Prompt | サンプルtxt            | build_prompt        | {{POINT}} {{REASON}} {{EXAMPLE}}含む      |
| IT-101  | Flow   | Discord testクライアント| /article+txt        | .md添付・Redis値=1                        |
| IT-102  | Flow   | 音声8MB 🎤リアクション   | 同上                | .md添付・Redis値=2                        |
| IT-103  | Limit  | 残回数5                | /article            | Embed「上限超過」                        |
| IT-104  | Role   | Premiumロール付与      | /article×20         | 全成功（Redis不減）                      |
| ST-201  | Load   | k6で12並列msg/s,60s    | スクリプト実行      | 成功率≥95%                                |
| ST-202  | Sec    | .exe添付               | /article            | 415 Unsupported                          |
| ST-203  | Sec    | presigned URL改ざん     | GETリクエスト        | 403 AccessDenied(moto)                    |

---

## 3. テストツール & ライブラリ
| ツール            | バージョン | 用途                  | 参考         |
|-------------------|------------|-----------------------|--------------|
| pytest            | ≥8.0       | フレームワーク        |              |
| fakeredis         | ≥2.21      | Redisモック           |              |
| moto[s3]          | ≥5.0       | S3/presignedモック    |              |
| discord.ext.test  | ≥1.5       | Discord APIシミュレーション |         |
| pytest-httpx      | ≥0.27      | OpenAI Stub           |              |
| k6                | ≥0.48      | 負荷試験              |              |

---

## 4. フォルダ構成例
```
tests/
  unit/
    test_limit.py
    test_prompt.py
  integration/
    test_article_flow.py
  system/
    k6_load.js
  security/
    test_mime.py
conftest.py        # fakeredis, moto, httpx fixtures
```

---

## 5. サンプルコード（赤→緑サイクル）
```python
# tests/unit/test_limit.py
import pytest
from mybot.limiter import limit_user, UsageLimitExceeded

def test_limit_increment(redis_client):
    for _ in range(5):
        ok = limit_user("123")
    assert ok is True

def test_limit_exceeded(redis_client):
    for _ in range(5):
        limit_user("999")
    with pytest.raises(UsageLimitExceeded):
        limit_user("999")
```
- redis_clientはfakeredisでset_response_callbackを使いTTLを擬似1日後へ設定

---

## 6. 実行手順 & CI
### 1. ローカル実行
```sh
pip install -r dev-requirements.txt
pytest -q
```
### 2. GitHub Actions
```yaml
- uses: actions/setup-python@v5
- run: pip install -r dev-requirements.txt
- run: pytest --cov=bot
```
- SecretsにOPENAI_API_KEYは不要（httpx stubで代替）

### 3. k6負荷テスト
```sh
k6 run tests/system/k6_load.js
```

---

## 7. 品質ゲート
| 指標                   | 基準値                |
|------------------------|-----------------------|
| 単体テストカバレッジ   | ≥90%                  |
| IT/STケース合格率      | 100%                  |
| k6成功率               | ≥95%（同時12msg/s）   |
| Banditセキュリティ     | CRITICAL 0件          |

---

## 8. 参考資料
1. Discordファイル上限
2. discord.ext.testモック解説
3. fakeredisドキュメント
4. Moto S3 presigned例
5. k6同時ユーザー設計ガイド
6. pytest-httpxでOpenAI Stub
7. Whisper API料金
8. ffmpeg音声抽出コマンド
9. Redis INCR+EXPIREパターン
10. Slash Commandで添付取得方法

---

これでテスト計画の穴埋め・粒度不足を解消し、赤→緑→リファクタのTDDループを回すための具体的な足場が整いました。 
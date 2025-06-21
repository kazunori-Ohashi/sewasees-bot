# 🤝 コントリビューションガイド

TDD Discord Botプロジェクトへのコントリビューションをありがとうございます！このガイドでは、プロジェクトへの貢献方法について説明します。

## 📋 目次

1. [貢献方法](#貢献方法)
2. [開発環境のセットアップ](#開発環境のセットアップ)
3. [コーディング規約](#コーディング規約)
4. [テスト](#テスト)
5. [プルリクエスト](#プルリクエスト)
6. [イシューレポート](#イシューレポート)
7. [リリースプロセス](#リリースプロセス)

---

## 貢献方法

### 🎯 歓迎する貢献

- **🐛 バグ修正**: 既知の問題の解決
- **✨ 新機能**: 新しい機能の追加
- **📚 ドキュメント**: ドキュメントの改善・翻訳
- **🧪 テスト**: テストカバレッジの向上
- **🔧 リファクタリング**: コード品質の改善
- **🚀 パフォーマンス**: 処理速度の最適化

### 🚫 貢献前の注意

- **大きな変更**: Issue で事前に議論してください
- **セキュリティ**: セキュリティ脆弱性は非公開で報告
- **ライセンス**: MIT ライセンスに同意が必要
- **品質**: TDD原則に従った開発

---

## 開発環境のセットアップ

### 1. リポジトリのフォーク

```bash
# GitHubでリポジトリをフォーク後
git clone https://github.com/YOUR_USERNAME/discord-bot-dev.git
cd discord-bot-dev

# アップストリームリモートを追加
git remote add upstream https://github.com/ORIGINAL_OWNER/discord-bot-dev.git
```

### 2. 開発環境構築

```bash
# Python仮想環境作成
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# または
.venv\Scripts\activate     # Windows

# 開発用依存関係インストール
pip install -r requirements.txt
pip install -r dev-requirements.txt  # 開発用パッケージ
```

### 3. 事前コミットフック設定

```bash
# pre-commit インストール
pip install pre-commit

# フック設定
pre-commit install

# 手動実行（オプション）
pre-commit run --all-files
```

**`.pre-commit-config.yaml`**:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
        additional_dependencies: [types-redis, types-requests]
```

### 4. 開発用設定

**`dev-requirements.txt`**:
```txt
# コード品質
black>=23.1.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.0.0

# テスト
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-asyncio>=0.21.0
pytest-mock>=3.10.0

# 開発ツール
pre-commit>=3.0.0
ipython>=8.0.0
jupyter>=1.0.0

# 型チェック
types-redis>=4.5.0
types-requests>=2.28.0
```

---

## コーディング規約

### 🐍 Python スタイルガイド

**PEP 8準拠** + プロジェクト固有ルール

#### 1. コードフォーマット

```python
# ✅ 良い例
async def process_file(
    content: bytes, 
    filename: str, 
    max_size: int = 10_000_000
) -> str:
    """
    ファイルを処理してテキストを返す
    
    Args:
        content: ファイルの内容
        filename: ファイル名
        max_size: 最大ファイルサイズ
    
    Returns:
        処理されたテキスト
        
    Raises:
        ValueError: ファイルサイズ超過時
    """
    if len(content) > max_size:
        raise ValueError(f"File too large: {len(content)} bytes")
    
    return content.decode("utf-8")


# ❌ 悪い例
def process_file(content,filename,max_size=10000000):
    if len(content)>max_size:raise ValueError("File too large")
    return content.decode("utf-8")
```

#### 2. 型ヒント

```python
# ✅ 必須: 関数の引数・戻り値
async def generate_article(
    content: str, 
    style: Literal["prep", "pas"] = "prep"
) -> str:
    pass

# ✅ 推奨: 変数の型宣言
user_data: Dict[str, Any] = {}
file_types: List[str] = [".txt", ".pdf", ".mp3"]

# ✅ クラス属性
class TDDBot(commands.Bot):
    redis_client: Optional[redis.Redis]
    daily_rate_limit: int
```

#### 3. エラーハンドリング

```python
# ✅ 具体的な例外処理
try:
    result = await openai_api_call()
except openai.RateLimitError as e:
    logger.warning(f"Rate limit exceeded: {e}")
    await asyncio.sleep(60)
    result = await openai_api_call()
except openai.APIError as e:
    logger.error(f"OpenAI API error: {e}")
    raise ProcessingError(f"Failed to generate content: {e}")

# ❌ 避ける: 汎用例外キャッチ
try:
    result = await openai_api_call()
except Exception:
    pass  # エラーの詳細が分からない
```

#### 4. ログ出力

```python
# ✅ 適切なログレベル
logger.debug("Processing file: %s", filename)        # デバッグ情報
logger.info("Article generated for user %s", user_id) # 重要な処理
logger.warning("Rate limit approaching: %d", count)   # 警告
logger.error("Failed to process: %s", error)          # エラー
logger.critical("System failure: %s", error)         # 致命的エラー

# ✅ 構造化ログ
logger.info(
    "File processed successfully",
    extra={
        "user_id": user_id,
        "file_type": file_type,
        "file_size": file_size,
        "processing_time": processing_time
    }
)
```

### 📁 ディレクトリ構造

```
discord-bot-dev/
├── tdd_bot.py              # メインBot実装
├── requirements.txt        # 本番用依存関係
├── dev-requirements.txt    # 開発用依存関係
├── .pre-commit-config.yaml # コード品質チェック
├── tests/                  # テストファイル
│   ├── unit/              # ユニットテスト
│   ├── integration/       # 統合テスト
│   ├── system/           # システムテスト
│   └── conftest.py       # テスト設定
├── docs/                  # ドキュメント
│   ├── SETUP_GUIDE.md
│   ├── API_REFERENCE.md
│   └── DEPLOYMENT_GUIDE.md
└── examples/              # 使用例
    ├── basic_usage.py
    └── advanced_features.py
```

---

## テスト

### 🧪 TDD原則に従った開発

1. **Red**: 失敗するテストを先に書く
2. **Green**: テストを通す最小限のコードを書く
3. **Refactor**: コードを改善する

#### テスト例

**新機能追加の流れ**:

```python
# 1. Red: 失敗するテスト
def test_extract_keywords_from_text():
    text = "Python プログラミング 機械学習 データサイエンス"
    keywords = extract_keywords(text)
    
    assert len(keywords) >= 3
    assert "Python" in keywords
    assert "機械学習" in keywords

# 2. Green: 最小実装
def extract_keywords(text: str) -> List[str]:
    # 最小限の実装（あとで改善）
    return text.split()

# 3. Refactor: 改善実装
def extract_keywords(text: str) -> List[str]:
    """テキストからキーワードを抽出"""
    import re
    # より洗練された実装
    words = re.findall(r'\w+', text)
    return [word for word in words if len(word) > 2]
```

### 🏃 テスト実行

```bash
# 全テスト実行
python run_tests.py

# 特定のテスト実行
pytest tests/unit/test_limit.py -v

# カバレッジ付きテスト
pytest --cov=tdd_bot tests/

# 特定の機能のテスト
pytest -k "test_tldr" -v
```

### 📊 カバレッジ要件

- **最小カバレッジ**: 80%
- **推奨カバレッジ**: 90%+
- **重要機能**: 100% (セキュリティ、レート制限)

---

## プルリクエスト

### 📝 プルリクエスト作成手順

1. **ブランチ作成**
   ```bash
   git checkout -b feature/add-tldr-feature
   # または
   git checkout -b fix/rate-limit-bug
   ```

2. **変更の実装**
   ```bash
   # コードの変更
   # テストの追加・更新
   ```

3. **テスト実行**
   ```bash
   python run_tests.py
   pytest --cov=tdd_bot tests/
   ```

4. **コミット**
   ```bash
   git add .
   git commit -m "feat: add TLDR generation feature
   
   - Add generate_tldr() method to TDDBot class
   - Add /tldr slash command
   - Add TLDR option to /article command
   - Update tests and documentation"
   ```

5. **プッシュとプルリクエスト**
   ```bash
   git push origin feature/add-tldr-feature
   # GitHubでプルリクエスト作成
   ```

### 📋 プルリクエストテンプレート

```markdown
## 概要
<!-- 変更内容の簡潔な説明 -->

## 変更タイプ
- [ ] バグ修正
- [ ] 新機能
- [ ] ドキュメント更新
- [ ] リファクタリング
- [ ] テスト追加
- [ ] その他（詳細: ）

## 変更内容
<!-- 具体的な変更内容を記述 -->

## テスト
- [ ] 新しいテストを追加した
- [ ] 既存のテストを更新した
- [ ] すべてのテストが通ることを確認した
- [ ] カバレッジが適切に維持されている

## チェックリスト
- [ ] コードがプロジェクトのスタイルガイドに従っている
- [ ] 適切な型ヒントが追加されている
- [ ] ドキュメントが更新されている
- [ ] 破壊的変更がある場合、CHANGELOGに記載した

## 関連Issue
Closes #123
```

### 🔍 レビュープロセス

1. **自動チェック**: CI/CDでテスト・フォーマット確認
2. **コードレビュー**: メンテナーによるレビュー
3. **修正対応**: フィードバックに基づく修正
4. **マージ**: 承認後にメインブランチにマージ

---

## イシューレポート

### 🐛 バグレポート

```markdown
**バグの説明**
明確で簡潔なバグの説明

**再現手順**
1. '...' にアクセス
2. '...' をクリック
3. '...' を入力
4. エラーが発生

**期待される動作**
正常に動作するはずの内容

**実際の動作**
実際に起こった内容

**環境情報**
- OS: [Windows 10 / macOS 13 / Ubuntu 22.04]
- Python バージョン: [3.11.0]
- Bot バージョン: [2.0.0]

**追加情報**
- エラーログ
- スクリーンショット
- 関連する設定情報
```

### ✨ 機能リクエスト

```markdown
**機能リクエストの背景**
なぜこの機能が必要なのか

**提案する解決策**
どのような機能を実装したいか

**代替案**
他に考えられる解決策

**追加情報**
参考になる情報やリンク
```

---

## リリースプロセス

### 🏷️ バージョニング

**Semantic Versioning (SemVer)** を採用:
- **MAJOR** (1.0.0): 破壊的変更
- **MINOR** (1.1.0): 新機能追加（後方互換性あり）
- **PATCH** (1.1.1): バグ修正

### 📦 リリース手順

1. **バージョン更新**
   ```bash
   # バージョン番号更新
   vim tdd_bot.py  # __version__ = "2.1.0"
   ```

2. **CHANGELOG更新**
   ```markdown
   ## [2.1.0] - 2024-01-15
   
   ### Added
   - TLDR生成機能
   - 記事へのTLDR統合オプション
   
   ### Changed
   - OpenAI API呼び出しの最適化
   
   ### Fixed
   - PDF処理時のエンコーディングエラー
   ```

3. **リリースタグ作成**
   ```bash
   git tag -a v2.1.0 -m "Release version 2.1.0"
   git push origin v2.1.0
   ```

4. **GitHub Release作成**
   - リリースノート作成
   - バイナリ配布（必要に応じて）

---

## 📞 コミュニティ

### 💬 コミュニケーション

- **GitHub Issues**: バグ報告・機能リクエスト
- **GitHub Discussions**: 質問・アイデア討論
- **Discord**: リアルタイム議論（招待制）

### 🎖️ 貢献者認定

定期的に貢献者を認定し、プロジェクトページで紹介します：

- **Contributor**: 1回以上のPR
- **Regular Contributor**: 5回以上のPR
- **Core Contributor**: 継続的な貢献
- **Maintainer**: プロジェクト管理権限

---

## 📜 ライセンス

このプロジェクトへの貢献により、あなたのコントリビューションはMITライセンスの下でライセンスされることに同意するものとします。

---

**Happy Contributing! 🚀**

あなたの貢献がプロジェクトをより良いものにします。質問や不明な点があれば、お気軽にIssueやDiscussionで質問してください。
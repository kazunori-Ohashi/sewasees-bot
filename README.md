# Discord Bot Project

このリポジトリは、多機能なDiscord Botを開発するためのプロジェクトです。

## 概要

このBotは、文章生成、SNS投稿支援、文字起こしなど、複数の機能を提供することを目的としています。
機能はサービスとしてモジュール化されており、拡張性の高い設計を目指しています。

## ディレクトリ構成

```
discord-bot-dev/
├── _docs/               # ドキュメント
├── bots/                # Bot本体のコード
│   └── writer_bot.py
├── common/              # 共通モジュール
│   ├── services/        # 外部サービス連携
│   ├── base_bot.py      # Botの基底クラス
│   └── ...
├── .env                 # 環境変数ファイル（各自で作成）
└── README.md
```

## セットアップ方法

### 1. 必要なライブラリのインストール

`bots/writer_bot.py` や `common/` 以下のファイルで `import` されているライブラリをインストールしてください。

例:
```bash
pip install discord.py python-dotenv tweepy openai
```
(プロジェクトに必要なライブラリは、後ほど `requirements.txt` にまとめることを推奨します。)

### 2. 環境変数の設定

プロジェクトのルートディレクトリに`.env`ファイルを作成し、Botの運用に必要な情報を記述してください。

```
# Discord Botのトークン
DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"

# OpenAI APIキー
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"

# Twitter(X) API v2の各種キー
TW_API_KEY="YOUR_TWITTER_API_KEY"
TW_API_SECRET="YOUR_TWITTER_API_SECRET"
TW_ACCESS_TOKEN="YOUR_TWITTER_ACCESS_TOKEN"
TW_ACCESS_SECRET="YOUR_TWITTER_ACCESS_SECRET"
```

## 起動方法

以下のコマンドをプロジェクトのルートディレクトリで実行してください。

```bash
python -m bots.writer_bot
```

**【重要】**
`-m`オプションを付けてモジュールとして実行することで、`common`ディレクトリなどの他モジュールを正しく読み込むことができます。`python bots/writer_bot.py` のように直接ファイルを指定して実行すると、`ModuleNotFoundError` が発生しますのでご注意ください。

## 主な機能 (`WriterBot`)

-   `/write <テキスト>`: トピックに基づいた文章を生成します。
-   `/tweet <テキスト>`: X (旧Twitter) に投稿します。
-   `/transcribe`: 添付された音声ファイルを文字起こしします。
-   `/clean <テキスト>`: テキストをMarkdown形式に整形します。
-   `/invite`: Botの招待リンクを生成します。
-   `/upgrade`: 料金プランの案内を表示します。
-   `/set_paid`, `/set_free`, `/my_plan`: ユーザーのプランを管理します。
-   ❤️リアクション: メッセージに❤️リアクションを付けると、その内容をX (旧Twitter) に投稿するための確認UIを表示します。

## 別途実装 (`simple_bot.py`)

こちらは `WriterBot` とは独立した、よりシンプルなBotの実装例です。

### 起動方法

```bash
python simple_bot.py
```
※ `simple_bot.py` はルートディレクトリに配置されているため、`-m` オプションは不要です。

### 主な機能

-   `書いて:<トピック>`: 指定されたトピックについて、ローカルのドキュメント（Vault）を参考に文章を生成し、結果をファイルに保存します。
-   通常のメッセージ送信: 送信された文章をLLMが整形・要約し、タイトルとタグを付けて返信します。
-   `?`: コマンド一覧を表示します。
-   ❤️リアクション: メッセージに❤️リアクションを付けると、X(Twitter)への投稿UIが表示されます。（こちらは `WriterBot` と同様の機能です）

## 🆕 2024-07 検索ロジック大幅改善

### 改善ポイント
- **日本語Vaultでの短文・固有名詞トピック（例：「沖縄県」）でも高精度にヒット**
- ノートごとに `meta`（ファイル名・aliases・tags）を優先的に部分一致検索
- トピックから命令語除去＋2文字以上の単語抽出でキーワードリスト化
- metaでヒットしない場合のみbody（本文）も含めて再検索
- RapidFuzzの`partial_ratio`で短文一致・部分一致に強いスコアリング
- どのキーワードで何点だったかをデバッグ出力し、ヒット理由を可視化

### 効果
- Vault内に「沖縄県」などのノートが存在すれば、bodyが長くてもmeta優先で確実にヒット
- 表記ゆれ・エイリアス・タグも検索対象となり、ヒット率が大幅向上
- 参考ノートが0件なら「なし」と明示、1件以上ならObsidianリンク形式で表示

--- 
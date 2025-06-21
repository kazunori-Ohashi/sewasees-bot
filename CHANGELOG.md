# Changelog

All notable changes to the TDD Discord Bot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing currently

### Changed
- Nothing currently

### Fixed
- Nothing currently

## [2.0.0] - 2024-06-24

### Added
- **🆕 TLDR生成機能**: 長文コンテンツの要約生成
  - `/tldr` コマンドで独立した要約生成
  - `/article` コマンドに `include_tldr` オプション追加
  - 3-5つの要点を絵文字付き箇条書きで表示
- **🔍 依存性チェック機能**: 起動時の自動依存関係検証
  - ffmpeg, Redis, OpenAI API, Discord Tokenの自動チェック
  - `check_dependencies()` 関数による事前検証
  - エラー時の詳細なトラブルシューティング情報
- **📄 完全なPDF処理**: pdfminer.sixによる高精度テキスト抽出
  - 従来の「not implemented」から完全実装に変更
  - 8000文字制限付きでトークン制限に対応
  - エラーハンドリングとエンコーディング対応
- **⚡ 非同期処理最適化**: subprocess の非同期化
  - `subprocess.run()` から `asyncio.create_subprocess_exec()` に変更
  - ffmpeg処理のブロッキング解消
  - 並列処理性能の向上
- **⚙️ 設定の完全外部化**:
  - Premiumロール名: `PREMIUM_ROLE_NAME` 環境変数
  - レート制限値: `DAILY_RATE_LIMIT` 環境変数
  - Redis設定: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` 環境変数
- **📊 管理ログ機能**: モデレーター向けの詳細活動ログ
  - Bot起動/停止、記事生成、エラーの自動通知
  - `MODERATOR_CHANNEL_ID` 環境変数でチャンネル指定
  - 使用統計とエラー監査ログ
- **📚 包括的ドキュメンテーション**:
  - 詳細セットアップガイド (`SETUP_GUIDE.md`)
  - 完全APIリファレンス (`API_REFERENCE.md`)
  - 本番デプロイメントガイド (`DEPLOYMENT_GUIDE.md`)
  - 開発者向けコントリビューションガイド (`CONTRIBUTING.md`)

### Changed
- **🏗️ アーキテクチャ図とファイル構成図の追加**: メインREADMEに詳細な構成情報
- **🧪 テストランナーの機能拡張**: 新機能のテストケース追加
- **📖 READMEの大幅改善**: 機能説明、トラブルシューティング、設定オプションの詳細化

### Fixed
- プロンプト生成での `{{POINT}}` プレースホルダーのエスケープ問題
- Redis接続エラー時の適切なフォールバック処理
- ファイル処理エラー時のログ出力改善

### Security
- ファイル形式検証の強化（既存機能の継続）
- 環境変数による秘密情報の適切な管理
- 実行ファイルの自動拒否機能（既存機能の継続）

## [1.0.0] - 2024-06-22

### Added
- **初回リリース**: TDD手法による Discord Bot 実装
- **📄 記事生成機能**: PREP/PAS形式のMarkdown記事作成
  - `/article` スラッシュコマンド
  - テキスト、PDF、音声、動画ファイル対応
  - PREP (Point-Reason-Example-Point) 形式
  - PAS (Problem-Agitation-Solution) 形式
- **🎤 音声認識機能**: OpenAI Whisper APIによる文字起こし
  - 🎤 リアクションでの音声・動画処理
  - FFmpeg による音声抽出
  - 複数音声形式対応 (.mp3, .wav, .m4a, .ogg)
  - 動画形式対応 (.mp4, .webm)
- **📊 使用回数管理**: Redis による日次レート制限
  - `/usage` コマンドで使用状況確認
  - 無料ユーザー: 5回/日制限
  - Premiumロール: 無制限利用
- **🔒 セキュリティ機能**:
  - 危険ファイル形式の自動拒否 (.exe, .bat等)
  - ファイルサイズ制限 (10MB)
  - MIME タイプ検証
- **📁 ファイル処理**:
  - テキストファイル: 複数エンコーディング対応
  - PDFファイル: 基本構造（簡易実装）
  - 音声ファイル: Whisper API 連携
  - 動画ファイル: FFmpeg + Whisper 連携
- **🧪 TDD テストスイート**:
  - ユニットテスト (rate limiting, prompt generation)
  - 統合テスト (article flow)
  - セキュリティテスト (MIME validation)
  - システムテスト (k6 load testing)
- **📋 基本ドキュメント**:
  - プロジェクト概要 README
  - 仕様書 (spec/ ディレクトリ)
  - テスト仕様書

### Technical Details
- **Language**: Python 3.8+
- **Framework**: discord.py 2.3+
- **AI Services**: OpenAI GPT-4o-mini, Whisper API
- **Database**: Redis (rate limiting)
- **Audio Processing**: FFmpeg
- **Testing**: pytest, fakeredis, moto
- **Architecture**: Single-file TDD implementation

---

## Version History Summary

| Version | Release Date | Key Features |
|---------|--------------|--------------|
| **2.0.0** | 2024-06-24 | TLDR機能、依存性チェック、完全PDF対応、非同期最適化、設定外部化、管理ログ |
| **1.0.0** | 2024-06-22 | 初回リリース、基本記事生成、音声認識、レート制限、セキュリティ |

---

## Development Philosophy

このプロジェクトは以下の原則に基づいて開発されています：

- **Test-Driven Development (TDD)**: テストファースト開発
- **Security First**: セキュリティを最優先
- **User Experience**: 使いやすさの重視
- **Performance**: 高速処理の追求
- **Documentation**: 包括的ドキュメンテーション
- **Maintainability**: 保守しやすいコード

---

## Migration Guide

### v1.0.0 → v2.0.0

**新機能**:
- `/tldr` コマンドが利用可能
- `/article` に `include_tldr` オプション追加
- 起動時依存性チェックが実行される

**設定変更** (オプション):
```bash
# 新しい環境変数 (.env に追加可能)
PREMIUM_ROLE_NAME=premium              # Premiumロール名をカスタマイズ
DAILY_RATE_LIMIT=5                     # レート制限値をカスタマイズ
MODERATOR_CHANNEL_ID=123456789012345678 # 管理ログチャンネル設定
```

**破壊的変更**: なし（完全下位互換）

---

## Contributors

- [@contributor1] - Initial implementation and TDD architecture
- [@contributor2] - TLDR feature development
- [@contributor3] - Documentation improvements
- [Community contributors] - Bug reports and feature suggestions

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Latest Update**: 2024-06-24
**Maintained by**: TDD Discord Bot Team
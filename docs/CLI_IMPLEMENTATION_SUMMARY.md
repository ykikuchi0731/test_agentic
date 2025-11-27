# CLI Implementation Summary

## 概要

exampleスクリプトの統合・整理を完了し、統合CLIツールを実装しました。

## 実装内容

### ✅ 完了したタスク

1. **共通CLIユーティリティの作成** (`cli_utils.py`)
   - 共通引数パーサー
   - フィルタリング機能
   - 制限・オフセット機能
   - ロギング設定
   - ドライラン機能

2. **統合CLIツールの作成** (`cli.py`)
   - `migrate` - フルマイグレーション
   - `export-list` - 記事リストエクスポート
   - `process-iframes` - iframe処理
   - `make-subitem` - Notionページ階層化
   - `visualize` - カテゴリ階層可視化

3. **モジュール直接実行の実装**
   - `pre_processing/__main__.py` - マイグレーション実行
   - `post_processing/__main__.py` - ポストプロセシング実行

4. **examplesディレクトリの整理**
   - 9ファイル → 3ファイルに集約
   - `quick_start.py` - クイックスタート
   - `full_migration.py` - フルマイグレーション
   - `README.md` - 使用例ドキュメント

5. **ドキュメント作成**
   - `docs/cli_reference.md` - 完全なCLIリファレンス
   - `examples/README.md` - 使用例
   - `README.md` - CLIセクション追加

### 🎯 達成した目標

#### 1. スクリプトの統合
**Before (9ファイル):**
```
examples/
├── export_article_list.py
├── export_google_doc.py
├── export_google_doc_browser.py
├── main.py
├── make_page_subitem.py
├── migration_example.py
├── post_import_example.py
├── process_iframes.py
└── visualize_hierarchy.py
```

**After (3ファイル):**
```
examples/
├── quick_start.py          # クイックスタート
├── full_migration.py       # フルマイグレーション
└── README.md              # ドキュメント
```

#### 2. CLIツールによる機能統合

**統一されたインターフェース:**
```bash
python cli.py migrate          # マイグレーション
python cli.py export-list      # 記事リストエクスポート
python cli.py make-subitem     # ページ階層化
python cli.py visualize        # 階層可視化
```

#### 3. 共通オプションの実装

すべてのコマンドで以下のオプションが使用可能:

- `--limit N` - 件数制限
- `--offset N` - オフセット
- `--filter "key:value"` - フィルタリング
- `--dry-run` - ドライラン
- `-v, --verbose` - 詳細ログ
- `-q, --quiet` - 最小限の出力

#### 4. テスト実行の簡素化

**Before (個別スクリプト作成が必要):**
```bash
# 新しいテストケースごとに新しいスクリプトを作成
python examples/test_5_articles.py
python examples/test_it_category.py
python examples/test_kb0001.py
```

**After (引数で制御):**
```bash
# 同じCLIツールで引数を変えるだけ
python cli.py migrate --limit 5
python cli.py migrate --filter "category:IT"
python cli.py migrate --filter "number:KB0001"
```

## 使用方法

### 基本的な使い方

```bash
# ヘルプ表示
python cli.py --help
python cli.py migrate --help

# クイックテスト（5記事）
python cli.py migrate --limit 5

# フルマイグレーション
python cli.py migrate

# フィルタリング
python cli.py migrate --filter "category:IT" --limit 100

# ドライラン
python cli.py migrate --filter "category:HR" --dry-run
```

### フィルタリング機能

```bash
# カテゴリでフィルタ
python cli.py migrate --filter "category:IT"

# 記事番号でフィルタ
python cli.py migrate --filter "number:KB0001"

# 複数フィルタ（AND条件）
python cli.py migrate --filter "category:IT" --filter "workflow_state:published"
```

### 件数制限・オフセット

```bash
# 最初の10件
python cli.py migrate --limit 10

# 50件スキップして次の10件
python cli.py migrate --offset 50 --limit 10

# バッチ処理
python cli.py migrate --offset 0 --limit 100    # バッチ1
python cli.py migrate --offset 100 --limit 100  # バッチ2
python cli.py migrate --offset 200 --limit 100  # バッチ3
```

### モジュール直接実行

```bash
# Pre-processing（マイグレーション）
python -m pre_processing --limit 10 --dry-run
python -m pre_processing --filter "category:IT"

# Post-processing
python -m post_processing make-subitem --child <id> --parent <id>
```

## ファイル構成

### 新規作成ファイル

```
test_agentic/
├── cli.py                           # 統合CLIツール ⭐新規
├── cli_utils.py                     # 共通CLIユーティリティ ⭐新規
│
├── pre_processing/
│   └── __main__.py                  # モジュール実行 ⭐新規
│
├── post_processing/
│   └── __main__.py                  # モジュール実行 ⭐新規
│
├── examples/
│   ├── quick_start.py               # クイックスタート ⭐新規
│   ├── full_migration.py            # フルマイグレーション ⭐新規
│   └── README.md                    # 使用例 ⭐新規
│
└── docs/
    └── cli_reference.md             # CLIリファレンス ⭐新規
```

### 削除ファイル

```
examples/
├── export_article_list.py           ❌削除
├── export_google_doc.py             ❌削除
├── export_google_doc_browser.py     ❌削除
├── main.py                          ❌削除
├── make_page_subitem.py             ❌削除
├── migration_example.py             ❌削除
├── post_import_example.py           ❌削除
├── process_iframes.py               ❌削除
└── visualize_hierarchy.py           ❌削除
```

## 利点

### 1. 開発効率の向上

**Before:**
- 新しいテストケースごとに新しいスクリプトを作成
- コードの重複が多い
- メンテナンスが困難

**After:**
- 引数で動作をカスタマイズ
- コードの再利用
- 一元管理

### 2. ユーザビリティの向上

**Before:**
```bash
# どのスクリプトを使えばいいか不明
ls examples/  # 9ファイル...どれを使う？
```

**After:**
```bash
# 明確なコマンド体系
python cli.py --help  # 全コマンドを確認
python cli.py migrate --help  # 特定コマンドのヘルプ
```

### 3. テストの簡素化

**Before:**
```python
# test_5_articles.py
articles = kb.get_all_articles()
articles = articles[:5]  # ハードコード
migrate(articles)
```

**After:**
```bash
# コマンドライン引数で制御
python cli.py migrate --limit 5
python cli.py migrate --limit 10
python cli.py migrate --limit 100
```

### 4. フィルタリングの柔軟性

```bash
# カテゴリ別
python cli.py migrate --filter "category:IT"
python cli.py migrate --filter "category:HR"

# 記事番号指定
python cli.py migrate --filter "number:KB0001"

# 複合条件
python cli.py migrate \
  --filter "category:IT" \
  --filter "workflow_state:published" \
  --limit 100
```

## ドキュメント

### 利用可能なドキュメント

1. **[CLI Reference](docs/cli_reference.md)** - 完全なCLIコマンドリファレンス
2. **[Examples README](examples/README.md)** - 使用例とベストプラクティス
3. **[Main README](README.md)** - プロジェクト概要とクイックスタート

### ヘルプコマンド

```bash
# メインヘルプ
python cli.py --help

# コマンド別ヘルプ
python cli.py migrate --help
python cli.py export-list --help
python cli.py make-subitem --help
```

## 今後の拡張

このCLI実装により、今後の機能追加が容易になりました：

### 新しいコマンドの追加

```python
# cli.py に新しいコマンドを追加するだけ

def cmd_new_feature(args):
    """新機能の実装"""
    # 実装...

# サブパーサーに追加
new_parser = subparsers.add_parser('new-feature', help='新機能')
CommonCLI.add_common_args(new_parser)  # 共通引数を自動追加
new_parser.set_defaults(func=cmd_new_feature)
```

### 新しいフィルタの追加

```python
# cli_utils.py の filter_articles() に追加

def filter_articles(articles, filters, kb_base):
    # 既存のフィルタ...

    # 新しいフィルタを追加
    if 'custom_field' in filters:
        filtered = [a for a in filtered if ...]

    return filtered
```

## まとめ

✅ **達成したこと:**
- exampleスクリプトを9ファイル→3ファイルに集約
- 統合CLIツールの実装
- 共通オプション（limit, filter, dry-run）の追加
- モジュール直接実行の実装
- 完全なドキュメント作成

✅ **改善されたこと:**
- 開発効率の向上
- コードの再利用性
- テストの簡素化
- ユーザビリティの向上
- メンテナンス性の向上

✅ **今後の展開:**
- 新機能の追加が容易
- 一貫したインターフェース
- 拡張性の確保

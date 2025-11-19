# Export Categories Feature

## 概要

ServiceNowのKnowledge Baseからカテゴリ階層を取得し、JSON/CSV形式でエクスポートする新しいCLIコマンドを追加しました。

## 新しいコマンド

### `export-categories`

カテゴリ階層を完全な形でエクスポートします。

**基本的な使い方:**

```bash
# JSONでエクスポート（デフォルト）
python cli.py export-categories

# CSVでエクスポート
python cli.py export-categories --format csv

# カスタム出力パス
python cli.py export-categories --output my_categories.json

# ドライラン（実行せずプレビュー）
python cli.py export-categories --dry-run
```

## 出力フォーマット

### JSON形式

階層構造を保持したまま出力します。

```json
[
  {
    "label": "IT",
    "full_path": "IT",
    "level": 0,
    "count": 150,
    "children": [
      {
        "label": "Applications",
        "full_path": "IT > Applications",
        "level": 1,
        "count": 50,
        "children": [
          {
            "label": "Figma",
            "full_path": "IT > Applications > Figma",
            "level": 2,
            "count": 10,
            "children": []
          }
        ]
      }
    ]
  },
  {
    "label": "HR",
    "full_path": "HR",
    "level": 0,
    "count": 80,
    "children": [
      {
        "label": "Benefits",
        "full_path": "HR > Benefits",
        "level": 1,
        "count": 25,
        "children": []
      }
    ]
  }
]
```

**フィールド説明:**
- `label` - カテゴリ名
- `full_path` - 完全なパス（親カテゴリを含む）
- `level` - 階層レベル（0=トップレベル）
- `count` - このカテゴリの記事数
- `children` - 子カテゴリの配列

### CSV形式

階層を平坦化して出力します。

```csv
category,full_path,level,article_count,parent_path
IT,IT,0,150,(root)
Applications,IT > Applications,1,50,IT
Figma,IT > Applications > Figma,2,10,IT > Applications
Slack,IT > Applications > Slack,2,15,IT > Applications
Hardware,IT > Hardware,1,30,IT
HR,HR,0,80,(root)
Benefits,HR > Benefits,1,25,HR
Policies,HR > Policies,1,20,HR
```

**カラム説明:**
- `category` - カテゴリ名
- `full_path` - 完全なパス
- `level` - 階層レベル
- `article_count` - 記事数
- `parent_path` - 親カテゴリのパス

## 使用例

### マイグレーション計画

カテゴリ構造を事前に確認してマイグレーション計画を立てる:

```bash
# カテゴリ階層をCSVで出力
python cli.py export-categories --format csv --output categories.csv

# CSVをExcelで開いて確認
# - どのカテゴリが多いか
# - 階層の深さはどのくらいか
# - どの順番でマイグレーションするか
```

### Notion構造の設計

エクスポートしたカテゴリ階層を元にNotion側の構造を設計:

```bash
# JSON形式でエクスポート
python cli.py export-categories --output categories.json

# JSONを見ながらNotionのデータベース構造を設計
# - どのカテゴリをデータベースにするか
# - どのカテゴリをタグにするか
# - どのカテゴリをページ階層にするか
```

### カテゴリ分析

記事の分布を分析:

```bash
# CSVでエクスポート
python cli.py export-categories --format csv

# CSVを分析ツールで開いて:
# - 記事数の多いカテゴリを特定
# - 空のカテゴリを見つける
# - 階層の深さを確認
```

### 自動処理の準備

プログラムで階層を処理する:

```python
import json

# JSONをロード
with open('category_hierarchy.json') as f:
    hierarchy = json.load(f)

# カテゴリごとに処理
def process_categories(nodes, parent=None):
    for node in nodes:
        print(f"Processing: {node['full_path']} ({node['count']} articles)")

        # このカテゴリの記事をマイグレーション
        migrate_category(node['label'])

        # 子カテゴリを再帰的に処理
        if node.get('children'):
            process_categories(node['children'], node)

process_categories(hierarchy)
```

## 既存コマンドとの比較

### `visualize` コマンド

- **目的**: ターミナルで視覚的に確認
- **出力**: テキストツリー表示のみ
- **用途**: 簡易確認

```bash
python cli.py visualize
```

出力例:
```
├─ IT (150 articles)
  ├─ Applications (50 articles)
    ├─ Figma (10 articles)
    ├─ Slack (15 articles)
  ├─ Hardware (30 articles)
├─ HR (80 articles)
  ├─ Benefits (25 articles)
```

### `export-categories` コマンド（新機能）

- **目的**: ファイルとしてエクスポート
- **出力**: JSON/CSV形式
- **用途**:
  - プログラムでの処理
  - Excelでの分析
  - ドキュメント化
  - 他ツールへのインポート

```bash
python cli.py export-categories --format csv
```

## オプション

### `--format {json,csv}`

出力フォーマットを指定します。

- `json` (デフォルト) - 階層構造を保持
- `csv` - 平坦化してスプレッドシートで扱いやすく

### `--output PATH`

出力ファイルパスを指定します。

- 指定なし: `category_hierarchy.json` または `category_hierarchy.csv`
- 指定あり: 指定したパス

### `--dry-run`

実際にエクスポートせず、何が出力されるかプレビューします。

```bash
python cli.py export-categories --dry-run
```

出力例:
```
[DRY RUN] Would export category hierarchy:
  - Top-level categories: 5
  - Output format: json
  - Output path: category_hierarchy.json
```

### `-v, --verbose`

詳細なログを出力します。

```bash
python cli.py export-categories -v
```

### `-q, --quiet`

エラーのみ出力します（最小限の出力）。

```bash
python cli.py export-categories -q
```

## 技術詳細

### 実装

`cli.py` に新しい関数 `cmd_export_categories()` を追加:

1. ServiceNowから全記事を取得
2. `CategoryHierarchyBuilder` で階層を構築
3. 指定されたフォーマット（JSON/CSV）で出力

### データフロー

```
ServiceNow API
    ↓
全記事取得 (kb.get_all_articles())
    ↓
階層構築 (CategoryHierarchyBuilder)
    ↓
フォーマット変換 (JSON/CSV)
    ↓
ファイル出力
```

### CSV平坦化アルゴリズム

階層構造を再帰的に走査し、各ノードを1行として出力:

```python
def flatten_hierarchy(nodes, parent_path="", rows=None):
    if rows is None:
        rows = []

    for node in nodes:
        full_path = f"{parent_path} > {node['label']}" if parent_path else node['label']
        rows.append({
            'category': node['label'],
            'full_path': full_path,
            'level': node.get('level', 0),
            'article_count': node.get('count', 0),
            'parent_path': parent_path or '(root)'
        })

        if node.get('children'):
            flatten_hierarchy(node['children'], full_path, rows)

    return rows
```

## よくある質問

### Q: カテゴリのみ取得し、記事は取得しませんか？

A: はい、このコマンドはカテゴリ階層のみを取得します。ただし、階層を構築するために全記事のメタデータ（カテゴリ情報）は取得します。記事の本文やHTMLは取得しません。

### Q: 大量の記事がある場合、時間がかかりますか？

A: 記事数に比例して時間がかかりますが、最適化されているため比較的高速です。進捗を確認したい場合は `-v` オプションを使用してください。

### Q: JSON と CSV、どちらを使うべきですか？

A: 用途によります:
- **JSON**: プログラムで処理する場合、階層構造を保持したい場合
- **CSV**: Excelで分析する場合、平坦なデータが扱いやすい場合

### Q: 空のカテゴリも出力されますか？

A: はい、記事が0件のカテゴリも出力されます（`count: 0`）。

### Q: カテゴリ名に特殊文字が含まれる場合は？

A: UTF-8でエンコードされるため、日本語やその他の特殊文字も問題なく出力されます。

## 関連コマンド

- `python cli.py visualize` - カテゴリ階層をターミナルで表示
- `python cli.py export-list` - 記事リストをエクスポート
- `python cli.py migrate` - 完全なマイグレーション実行

## まとめ

✅ **追加した機能:**
- カテゴリ階層のJSON/CSVエクスポート
- ドライラン機能
- カスタム出力パス
- 詳細ログオプション

✅ **用途:**
- マイグレーション計画
- Notion構造設計
- カテゴリ分析
- 自動処理の準備

✅ **出力形式:**
- JSON: 階層構造を保持
- CSV: 平坦化してExcel対応

この機能により、マイグレーション前にカテゴリ構造を十分に理解し、計画的に進めることができます！

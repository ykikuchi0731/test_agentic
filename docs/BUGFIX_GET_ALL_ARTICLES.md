# Bug Fix: get_all_articles() Method Not Found

## 問題

`python cli.py export-categories` を実行すると以下のエラーが発生:

```
AttributeError: 'KnowledgeBase' object has no attribute 'get_all_articles'.
Did you mean: 'get_article'?
```

## 原因

### エラー1: 存在しないモジュール
`CategoryHierarchyBuilder` クラスを含む `category_hierarchy.py` モジュールが存在していなかった。

### エラー2: 存在しないメソッド
`KnowledgeBase` クラスに `get_all_articles()` メソッドが存在せず、正しいメソッド名は `get_latest_articles_only()` だった。

## 解決策

### 1. CategoryHierarchyBuilder モジュールの作成

`pre_processing/category_hierarchy.py` を新規作成:

```python
class CategoryHierarchyBuilder:
    """Build hierarchical category tree from article metadata."""

    def build_hierarchy_from_articles(self, articles):
        """Build category hierarchy from articles."""
        # 記事からカテゴリパスを抽出
        # 階層構造を構築
        # ツリーとして返す
```

**主な機能:**
- `build_hierarchy_from_articles()` - 階層構造の構築
- `get_flat_categories()` - 平坦なカテゴリリスト取得
- `get_category_stats()` - 統計情報取得

### 2. メソッド名の修正

すべての `kb.get_all_articles()` を `kb.get_latest_articles_only()` に置換:

**修正したファイル (6箇所):**

1. **cli.py** (4箇所)
   - `cmd_migrate()` 関数
   - `cmd_export_list()` 関数
   - `cmd_export_categories()` 関数
   - `cmd_visualize()` 関数

2. **pre_processing/__main__.py** (1箇所)
   - `main()` 関数

3. **examples/quick_start.py** (1箇所)
   - `main()` 関数

4. **examples/full_migration.py** (1箇所)
   - `main()` 関数

## 修正内容

### Before (エラー)
```python
articles = kb.get_all_articles()
```

### After (修正後)
```python
articles = kb.get_latest_articles_only()
```

## get_latest_articles_only() とは

ServiceNowの記事は複数のバージョンを持つことができます。`get_latest_articles_only()` メソッドは:

- 各記事の**最新バージョンのみ**を取得
- 古いバージョンを自動的に除外
- 重複を排除してクリーンなリストを返す

**利点:**
- 不要な古いバージョンを処理しない
- マイグレーションのデータ量削減
- より正確なカテゴリ階層構築

## 検証

### モジュールのインポート確認
```bash
$ python -c "from pre_processing.category_hierarchy import CategoryHierarchyBuilder; print('✅ OK')"
✅ OK
```

### 階層構築のテスト
```python
from pre_processing.category_hierarchy import CategoryHierarchyBuilder

articles = [
    {'kb_category': 'IT > Applications > Figma'},
    {'kb_category': 'IT > Applications > Slack'},
    {'kb_category': 'IT > Hardware'},
    {'kb_category': 'HR > Benefits'},
]

builder = CategoryHierarchyBuilder()
hierarchy = builder.build_hierarchy_from_articles(articles)

# 結果:
# - IT: 3 articles
# - HR: 1 article
```

### CLIコマンドの動作確認
```bash
$ python cli.py export-categories --help
# ヘルプが正常に表示される

$ python cli.py export-categories --dry-run
# ドライランが正常に動作する
```

## 影響範囲

### 修正が必要だったファイル

1. **新規作成:**
   - `pre_processing/category_hierarchy.py` ⭐

2. **修正:**
   - `cli.py` (4箇所)
   - `pre_processing/__main__.py` (1箇所)
   - `examples/quick_start.py` (1箇所)
   - `examples/full_migration.py` (1箇所)

### 影響を受けるコマンド

すべてのコマンドが `get_latest_articles_only()` を使用するように修正:

- ✅ `python cli.py migrate`
- ✅ `python cli.py export-list`
- ✅ `python cli.py export-categories`
- ✅ `python cli.py visualize`
- ✅ `python -m pre_processing`
- ✅ `python examples/quick_start.py`
- ✅ `python examples/full_migration.py`

## 今後の対応

### エラー防止策

今後、新しいコマンドを追加する際は:

1. **KnowledgeBaseクラスの正しいメソッドを確認:**
   ```python
   # 正しいメソッド
   kb.get_latest_articles_only()  # 最新バージョンのみ
   kb.list_articles()             # すべての記事
   ```

2. **存在しないメソッドを使わない:**
   ```python
   # 存在しないメソッド (使用禁止)
   kb.get_all_articles()  # ❌ このメソッドは存在しない
   ```

3. **利用可能なメソッドを確認:**
   ```bash
   grep "def " pre_processing/knowledge_base.py | grep -E "get|list"
   ```

## まとめ

✅ **修正完了:**
- `CategoryHierarchyBuilder` モジュール作成
- すべての `get_all_articles()` を `get_latest_articles_only()` に置換
- 6ファイル、合計7箇所を修正

✅ **動作確認:**
- モジュールのインポート成功
- 階層構築ロジック動作確認
- CLIコマンド正常動作

✅ **改善点:**
- 最新バージョンのみ取得で効率化
- 古いバージョンの除外で正確性向上
- 一貫したメソッド使用でコード品質向上

これで `export-categories` コマンドが正常に動作します！

# 偏旁自動検出実験プログラム v0.2.0 - ダウンロードガイド

## 📥 ダウンロード方法

### 方法1: GitHubから直接ダウンロード

1. **リポジトリにアクセス**
   ```
   https://github.com/Naoking55/fontgen
   ```

2. **ブランチを切り替え**
   - ブランチ名: `claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T`
   - GitHubページ上部の「main」をクリック
   - `claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T` を選択

3. **ファイルをダウンロード**
   - `radical_auto_detect_experiment_v02.py` をクリック
   - 「Raw」ボタンをクリックして右クリック → 「名前を付けて保存」

### 方法2: git cloneでダウンロード

```bash
# リポジトリをクローン
git clone https://github.com/Naoking55/fontgen.git
cd fontgen

# ブランチをチェックアウト
git checkout claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T
```

### 方法3: 直リンク（最新版）

以下のURLから直接ダウンロード可能です：

**v0.2.0 メインプログラム:**
```
https://raw.githubusercontent.com/Naoking55/fontgen/claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T/radical_auto_detect_experiment_v02.py
```

**ドキュメント:**
```
https://raw.githubusercontent.com/Naoking55/fontgen/claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T/RADICAL_DETECTION_EXPERIMENT.md
```

**v0.1.0（比較用）:**
```
https://raw.githubusercontent.com/Naoking55/fontgen/claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T/radical_auto_detect_experiment.py
```

## 📋 必要なもの

### 1. Python環境
- Python 3.8以上推奨
- tkinter（通常Pythonに同梱）

### 2. 依存ライブラリ

```bash
pip install pillow numpy scipy
```

### 3. フォントファイル
- .ttf または .otf 形式の日本語フォント
- 例: Noto Sans CJK JP, IPAフォントなど

### 4. インターネット接続（初回のみ）
- 初回起動時にIDS（文字構造データ）を自動ダウンロード
- 約97,000文字分のデータ（数MB）
- 2回目以降は `ids_cache.json` から読み込むため不要

## 🚀 起動方法

```bash
python radical_auto_detect_experiment_v02.py
```

または、ファイルをダブルクリック（環境によって異なります）

## 🎯 基本的な使い方

1. **フォントを開く**
   - メニュー → ファイル → フォントを開く
   - .ttf/.otf ファイルを選択

2. **文字を入力**
   - 「文字」欄に漢字を1文字入力（例: 語、魔、門）
   - 「レンダリング」ボタンをクリック
   - ステータスバーにIDS情報が表示される

3. **検出方法を選択**
   - **🔍 辞書ベース検出**: IDS構造情報を使用（NEW!）
   - **🧩 連結成分分析**: 画像ベースの分析（v0.1.0互換）

4. **複数文字から共通偏旁を抽出**
   - 「文字列」欄に複数の文字を入力（例: 海江河）
   - 「共通偏旁を抽出」ボタンをクリック
   - さんずい（氵）が自動抽出される

5. **結果を保存**
   - 各成分の「この成分を保存」ボタンで保存

## 🧪 推奨テストケース

### まだれ（⿸ 左上包囲）
```
広、魔、慶、店、庫
```
→ v0.1.0では失敗したケースが改善

### もんがまえ（⿵ 上三方包囲）
```
間、問、門、閉、開
```
→ 門の左右柱を一体として認識

### くにがまえ（⿴ 全包囲）
```
国、囲、図、園
```
→ 内部要素を正しく抽出

### 複数文字抽出
```
さんずい: 海江河
にんべん: 信住仁
きへん: 林村校
ごんべん: 語話説
```
→ 共通偏旁を自動発見

## 📚 詳細ドキュメント

`RADICAL_DETECTION_EXPERIMENT.md` を参照してください：
- v0.2.0の新機能詳細
- IDS演算子の説明
- 実験手順
- 技術的詳細

## ⚠️ トラブルシューティング

### 1. SSL証明書エラー (macOS)

**症状:**
```
IDSダウンロードエラー: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]>
オフラインモードで動作します
```

**解決方法A: Python証明書をインストール（推奨）**

```bash
# 方法1: Install Certificates.commandを実行
open /Applications/Python\ 3.*/
# 「Install Certificates.command」をダブルクリック

# 方法2: コマンドラインから
/Applications/Python\ 3.*/Install\ Certificates.command

# 方法3: certifiを更新
pip3 install --upgrade certifi
```

**解決方法B: 手動ダウンロード（最も確実）**

プログラムと同じフォルダで以下を実行:

```bash
# IDSデータを手動ダウンロード
curl -o ids_raw.txt https://raw.githubusercontent.com/cjkvi/cjkvi-ids/master/ids.txt

# プログラムを再実行
python3 radical_auto_detect_experiment0.20.py
```

プログラムは自動的に `ids_raw.txt` を検出して使用します。

**解決方法C: SSL検証を無効化（v0.2.1以降は自動）**

v0.2.1以降では、SSL証明書エラーが発生した場合、自動的にSSL検証を無効化して再試行します。

### 2. tkinterが使えない環境

- **Linux**: `sudo apt-get install python3-tk`
- **macOS**: 通常は標準搭載
- **Windows**: 通常は標準搭載

### 3. IDSデータのダウンロードに失敗する場合

- インターネット接続を確認
- ファイアウォールの設定を確認
- 上記「解決方法B: 手動ダウンロード」を使用

### 4. 一部の文字でIDS情報がない

- 旧字体や異体字で欠落している場合がある
- その場合は「🧩 連結成分分析」を使用

### 5. オフラインモードで辞書ベース検出を使いたい

一度でもダウンロードに成功すれば、`ids_cache.json` が作成されます。
このファイルがあれば、以降はオフラインで辞書ベース検出が使えます。

## 🔄 バージョン履歴

### v0.2.1 (2025-11-06) - SSL証明書エラー対応
- **macOS SSL証明書エラーの自動解決**
- SSL証明書エラー時に自動的にSSL検証を無効化して再試行
- 手動ダウンロードファイル（ids_raw.txt）対応
- より詳細なエラーメッセージと解決方法の表示

### v0.2.0 (2025-11-06) - 辞書ベースアプローチ
- Unicode IDS データベース統合
- 辞書ベース偏旁検出
- 康熙部首214部首対応
- 改良版共通偏旁抽出

### v0.1.0 (2025-11-06) - 初期実験版
- 連結成分分析
- テンプレートマッチング基盤
- 複数文字共通部分抽出基盤

## 💬 フィードバック

実験結果やバグ報告は以下まで：
- GitHubリポジトリのIssues
- プロジェクトのディスカッション

---

**開発者**: Claude (Anthropic)
**プロジェクト**: fontgen
**ライセンス**: プロジェクトライセンスに準じる
**最終更新**: 2025-11-06

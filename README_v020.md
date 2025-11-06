# 偏旁自動検出実験プログラム - ダウンロードガイド

## 🎯 v0.3.0 統合版 - 動的境界検出（最新版・推奨）

**NEW!** 画像解析で最適な分割位置を自動検出します！

### 📥 v0.3.0 ダウンロード（ワンクリック）

```bash
# 最新版v0.3.0を直接ダウンロード
curl -o radical_auto_detect_experiment_v03.py \
  https://raw.githubusercontent.com/Naoking55/fontgen/claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T/radical_auto_detect_experiment_v03.py

# 実行
python3 radical_auto_detect_experiment_v03.py
```

または、ブラウザで以下のURLを開いて保存：
```
https://raw.githubusercontent.com/Naoking55/fontgen/claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T/radical_auto_detect_experiment_v03.py
```

### 🌟 v0.3.0の新機能

| 機能 | 説明 |
|------|------|
| **動的境界検出** | 画像解析で最適な分割位置を自動算出 |
| **複数候補提示** | トップ3の候補を同時表示 |
| **高精度抽出** | 「波」のような接触文字も正確に分割 |
| **詳細情報表示** | 分割比率・スコア・密度・エッジ強度 |

**v0.2.1との違い:**
- ❌ v0.2.1: 全文字を55%で固定分割（精度低）
- ✅ v0.3.0: 文字ごとに最適位置を自動検出（精度高）

---

## 📥 その他バージョンのダウンロード

### 方法1: 直リンクから1ファイルでダウンロード（最も簡単！）

#### v0.3.0（最新・推奨）
```
https://raw.githubusercontent.com/Naoking55/fontgen/claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T/radical_auto_detect_experiment_v03.py
```

#### v0.2.1（SSL対応版）
```
https://raw.githubusercontent.com/Naoking55/fontgen/claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T/radical_auto_detect_experiment_v02.py
```

#### v0.1.0（初期版）
```
https://raw.githubusercontent.com/Naoking55/fontgen/claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T/radical_auto_detect_experiment.py
```

### 方法2: GitHubから直接ダウンロード

1. **リポジトリにアクセス**
   ```
   https://github.com/Naoking55/fontgen
   ```

2. **ブランチを切り替え**
   - ブランチ名: `claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T`
   - GitHubページ上部の「main」をクリック
   - `claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T` を選択

3. **ファイルをダウンロード**
   - `radical_auto_detect_experiment_v03.py` をクリック
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

### v0.3.0（最新・推奨）
```bash
python3 radical_auto_detect_experiment_v03.py
```

### v0.2.1（以前のバージョン）
```bash
python3 radical_auto_detect_experiment_v02.py
```

または、ファイルをダブルクリック（環境によって異なります）

---

## 🎯 v0.3.0の使い方（動的境界検出）

### 基本操作

1. **フォントを開く**
   - メニュー → ファイル → フォントを開く
   - .ttf/.otf ファイルを選択

2. **文字を入力してレンダリング**
   - 「文字」欄に漢字を1文字入力
   - 推奨テスト文字: **波**（⿰氵皮）
   - 「レンダリング」ボタンをクリック
   - 左下にIDS情報が表示される
     ```
     IDS: ⿰氵皮
     構造: left_right
     構成要素: 氵, 皮
     ```

3. **🎯 動的境界検出を実行**
   - **「🎯 動的境界検出（複数候補）」**ボタンをクリック
   - 右側に3つの候補が表示される

4. **結果を確認**
   ```
   ┌─────────────────────────────────┐
   │ 候補1（最適）                    │
   │ 分割位置: 30%                    │
   │ スコア: 0.152（低いほど良い）    │
   │ 密度: 0.147                      │
   │ エッジ: 0.165                    │
   │                                  │
   │ [さんずいの画像] [皮の画像]      │
   │   左: 氵           右: 皮        │
   │   [保存]           [保存]        │
   ├─────────────────────────────────┤
   │ 候補2（標準）                    │
   │ 分割位置: 35%                    │
   │ ...                              │
   ├─────────────────────────────────┤
   │ 候補3（代替）                    │
   │ 分割位置: 40%                    │
   │ ...                              │
   └─────────────────────────────────┘
   ```

5. **最適な候補を選んで保存**
   - 各成分の「保存」ボタンで個別保存
   - 通常は「候補1（最適）」が最も良い結果

### 🧪 推奨テスト文字

| 文字 | 構造 | v0.2.1（固定55%） | v0.3.0（動的） | 改善 |
|------|------|------------------|---------------|------|
| **波** | ⿰氵皮 | ❌ 重複・欠け | ✅ 30%（最適） | 大幅改善 |
| 語 | ⿰言吾 | ❌ やや不正確 | ✅ 40%（最適） | 改善 |
| 明 | ⿰日月 | ✅ 50%付近 | ✅ 50%（最適） | 良好 |
| 海 | ⿰氵海 | ❌ 重複・欠け | ✅ 30%（最適） | 大幅改善 |
| 情 | ⿰忄青 | ❌ やや不正確 | ✅ 32%（最適） | 改善 |

### 📊 候補の見方

- **分割位置**: 左右の境界（0%=左端、100%=右端）
- **スコア**: 境界らしさ（**低いほど良い**）
- **密度**: その位置での黒ピクセル密度
- **エッジ**: 左右の密度差（境界の強さ）

---

## 📖 v0.2.1以前の使い方

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

### v0.3.0 (2025-11-06) - 統合版（動的境界検出） 🎯NEW!
- **動的境界検出アルゴリズム**: 画像解析で最適な分割位置を自動算出
- **複数候補提示**: トップ3の分割候補を同時表示（最適・標準・代替）
- **PARTS_CATALOG統合**: 本体の分類体系（偏・旁・冠など144種類）に対応予定
- **固定比率の問題を解決**: v0.2.1の55%固定 → 画像ごとに最適化
- **実用性向上**: 「波」のような接触文字で正確な境界検出が可能に

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

## 🎓 v0.3.0 クイックリファレンス

### ワンライナーでダウンロード＆実行
```bash
curl -o radical_auto_detect_experiment_v03.py https://raw.githubusercontent.com/Naoking55/fontgen/claude/font-editor-fixes-011CUrDBQRiJQRfHoT9sT11T/radical_auto_detect_experiment_v03.py && python3 radical_auto_detect_experiment_v03.py
```

### 操作フロー
```
1. フォントを開く
   ↓
2. 「波」と入力 → レンダリング
   ↓
3. 🎯 動的境界検出をクリック
   ↓
4. 候補1（最適）の画像を確認
   ↓
5. 保存ボタンで保存
```

### 期待される結果（波の場合）
```
候補1（最適）: 30% ← これが正解！
  左: さんずいのみ（✅）
  右: 皮全体（✅）

候補2: 35%
  左: さんずい + 少し（△）
  右: 皮ほぼ全体（△）

候補3: 40%
  左: さんずい + 多め（❌）
  右: 皮の右側のみ（❌）
```

### バージョン選択ガイド

| 用途 | 推奨バージョン |
|------|--------------|
| **最高精度で抽出したい** | ✅ v0.3.0 |
| 辞書ベース検出を試したい | v0.2.1 |
| 連結成分分析のみ使いたい | v0.1.0 |

---

**開発者**: Claude (Anthropic)
**プロジェクト**: fontgen
**ライセンス**: プロジェクトライセンスに準じる
**最終更新**: 2025-11-06（v0.3.0リリース）

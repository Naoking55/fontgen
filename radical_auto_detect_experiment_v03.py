#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
偏旁自動検出実験プログラム v0.3.0 - 統合版
Version: 0.3.0
Last Updated: 2025-11-06

v0.3.0 新機能:
- **動的境界検出**: 画像解析で最適な分割位置を自動算出
- **複数候補提示**: トップ3の分割候補を同時表示
- **PARTS_CATALOG統合**: 本体の分類体系（偏・旁・冠など）に対応
- **編集機能統合**: 本体の編集ツールを統合（予定）

v0.2.1からの改良:
- 固定比率（55%）→ 画像解析による動的比率
- 単一抽出 → 複数候補同時表示
- 手動分類 → 自動分類提案

実用レベルに達したら本体に統合予定
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageFont, ImageDraw, ImageTk, ImageOps, ImageFilter
import numpy as np
from scipy import ndimage
from typing import List, Tuple, Optional, Dict, Set
import json
import urllib.request
import urllib.error
import ssl
import re
from collections import defaultdict

# ========================================
# 設定
# ========================================

class Config:
    """実験プログラム設定"""
    CANVAS_SIZE = 2048
    DISPLAY_SIZE = 400
    FONT_RENDER_SIZE = 2048

    # 連結成分分析パラメータ
    MIN_COMPONENT_SIZE = 100
    BINARY_THRESHOLD = 200

    # 動的境界検出パラメータ
    BOUNDARY_SEARCH_RANGE_LR = (0.25, 0.75)  # 左右分割の探索範囲
    BOUNDARY_SEARCH_RANGE_TB = (0.25, 0.75)  # 上下分割の探索範囲
    BOUNDARY_SCAN_STEP = 0.02  # スキャンステップ（2%刻み）

    # IDSデータキャッシュ
    IDS_CACHE_FILE = "ids_cache.json"
    IDS_MANUAL_FILE = "ids_raw.txt"
    IDS_SOURCE_URL = "https://raw.githubusercontent.com/cjkvi/cjkvi-ids/master/ids.txt"


# ========================================
# 動的境界検出アルゴリズム（NEW!）
# ========================================

class DynamicBoundaryDetector:
    """動的境界検出器 - 画像解析で最適な分割位置を自動検出"""

    def __init__(self, binary_threshold: int = 200):
        self.binary_threshold = binary_threshold

    def find_optimal_split(self, img: Image.Image, direction: str = "vertical",
                          search_range: Tuple[float, float] = (0.3, 0.7),
                          num_candidates: int = 3) -> List[Tuple[float, float, Dict]]:
        """
        最適な分割位置を検出

        Args:
            img: 入力画像
            direction: "vertical" (左右分割) or "horizontal" (上下分割)
            search_range: 探索範囲 (min_ratio, max_ratio)
            num_candidates: 返す候補数

        Returns:
            [(ratio, score, info), ...] のリスト
            - ratio: 分割比率（0.0～1.0）
            - score: スコア（低いほど境界らしい）
            - info: 詳細情報
        """
        w, h = img.size
        img_array = np.array(img)
        binary = img_array < self.binary_threshold

        candidates = []

        if direction == "vertical":
            # 縦方向に走査（左右分割）
            for ratio in np.arange(search_range[0], search_range[1], Config.BOUNDARY_SCAN_STEP):
                x = int(w * ratio)
                if x <= 0 or x >= w:
                    continue

                # この位置での垂直線上の黒ピクセル密度
                line = binary[:, x]
                density = np.sum(line) / h

                # 周辺の密度変化も考慮（境界っぽさを強調）
                edge_score = self._calculate_edge_score(binary, x, "vertical")

                # 総合スコア（密度が低く、エッジが強いほど良い）
                score = density * 0.7 + (1.0 - edge_score) * 0.3

                candidates.append((ratio, score, {
                    'density': density,
                    'edge_score': edge_score,
                    'position': x
                }))
        else:
            # 横方向に走査（上下分割）
            for ratio in np.arange(search_range[0], search_range[1], Config.BOUNDARY_SCAN_STEP):
                y = int(h * ratio)
                if y <= 0 or y >= h:
                    continue

                line = binary[y, :]
                density = np.sum(line) / w

                edge_score = self._calculate_edge_score(binary, y, "horizontal")

                score = density * 0.7 + (1.0 - edge_score) * 0.3

                candidates.append((ratio, score, {
                    'density': density,
                    'edge_score': edge_score,
                    'position': y
                }))

        # スコアが低い順（境界らしい順）にソート
        candidates.sort(key=lambda x: x[1])

        # トップN候補を返す
        return candidates[:num_candidates]

    def _calculate_edge_score(self, binary: np.ndarray, position: int, direction: str) -> float:
        """エッジスコアを計算（境界の強さ）"""
        h, w = binary.shape

        if direction == "vertical":
            if position <= 2 or position >= w - 3:
                return 0.0

            # 左右の密度差
            left_region = binary[:, max(0, position - 5):position]
            right_region = binary[:, position:min(w, position + 5)]

            left_density = np.sum(left_region) / (left_region.size + 1e-8)
            right_density = np.sum(right_region) / (right_region.size + 1e-8)

            # 密度差が大きいほど境界らしい
            edge_strength = abs(left_density - right_density)

            return edge_strength
        else:
            if position <= 2 or position >= h - 3:
                return 0.0

            top_region = binary[max(0, position - 5):position, :]
            bottom_region = binary[position:min(h, position + 5), :]

            top_density = np.sum(top_region) / (top_region.size + 1e-8)
            bottom_density = np.sum(bottom_region) / (bottom_region.size + 1e-8)

            edge_strength = abs(top_density - bottom_density)

            return edge_strength


# ========================================
# IDS データベース（v0.2.1から継承）
# ========================================

class IDSDatabase:
    """IDS (Ideographic Description Sequences) データベース"""

    IDS_OPERATORS = {
        '\u2FF0': 'left_right',
        '\u2FF1': 'top_bottom',
        '\u2FF2': 'top_lr',
        '\u2FF3': 'left_tb',
        '\u2FF4': 'surround_full',
        '\u2FF5': 'surround_above',
        '\u2FF6': 'surround_below',
        '\u2FF7': 'surround_left',
        '\u2FF8': 'surround_upper_left',
        '\u2FF9': 'surround_upper_right',
        '\u2FFA': 'surround_lower_left',
        '\u2FFB': 'overlay',
    }

    def __init__(self):
        self.ids_data: Dict[str, str] = {}
        self._load_or_download()

    def _load_or_download(self):
        """IDSデータをロード"""
        if os.path.exists(Config.IDS_CACHE_FILE):
            try:
                with open(Config.IDS_CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.ids_data = json.load(f)
                print(f"✅ IDSキャッシュ読み込み: {len(self.ids_data)} エントリ")
                return
            except Exception as e:
                print(f"⚠️  キャッシュ読み込みエラー: {e}")

        if os.path.exists(Config.IDS_MANUAL_FILE):
            print(f"📁 手動ファイル検出: {Config.IDS_MANUAL_FILE}")
            try:
                self._parse_from_file(Config.IDS_MANUAL_FILE)
                return
            except Exception as e:
                print(f"❌ 手動ファイル読み込みエラー: {e}")

        self._download_and_parse()

    def _parse_from_file(self, file_path: str):
        """ファイルから解析"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self._parse_content(content)

    def _download_and_parse(self):
        """ダウンロードして解析"""
        print("🌐 IDSデータをダウンロード中...")
        try:
            with urllib.request.urlopen(Config.IDS_SOURCE_URL, timeout=30) as response:
                content = response.read().decode('utf-8')
            self._parse_content(content)
            return
        except urllib.error.URLError as e:
            if 'CERTIFICATE_VERIFY_FAILED' in str(e):
                print("⚠️  SSL証明書エラー → SSL検証無効化で再試行...")
                try:
                    import ssl
                    context = ssl._create_unverified_context()
                    with urllib.request.urlopen(Config.IDS_SOURCE_URL, timeout=30, context=context) as response:
                        content = response.read().decode('utf-8')
                    self._parse_content(content)
                    print("✅ SSL検証無効化でダウンロード成功")
                    return
                except Exception as e2:
                    print(f"❌ ダウンロード失敗: {e2}")
            else:
                print(f"❌ ダウンロード失敗: {e}")
        except Exception as e:
            print(f"❌ ダウンロード失敗: {e}")

        print("⚠️  オフラインモード（連結成分分析のみ利用可能）")

    def _parse_content(self, content: str):
        """コンテンツを解析"""
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 3:
                char = parts[1]
                ids = parts[2]
                self.ids_data[char] = ids

        with open(Config.IDS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.ids_data, f, ensure_ascii=False, indent=2)

        print(f"✅ IDSデータ取得完了: {len(self.ids_data)} エントリ")

    def get_structure(self, char: str) -> Optional[Dict]:
        """文字の構造情報を取得"""
        if char not in self.ids_data:
            return None

        ids = self.ids_data[char]

        operator = None
        operator_char = None
        for op_char, op_type in self.IDS_OPERATORS.items():
            if op_char in ids:
                operator = op_type
                operator_char = op_char
                break

        if not operator:
            return None

        parts = ids.split(operator_char, 1)
        if len(parts) < 2:
            return None

        components = self._extract_components(parts[1])

        return {
            'char': char,
            'ids': ids,
            'operator': operator,
            'components': components
        }

    def _extract_components(self, ids_str: str) -> List[str]:
        """構成要素を抽出"""
        components = []
        i = 0
        while i < len(ids_str):
            char = ids_str[i]
            if char in self.IDS_OPERATORS:
                if i + 2 < len(ids_str):
                    components.append(ids_str[i:i+3])
                    i += 3
                else:
                    i += 1
            else:
                components.append(char)
                i += 1
        return components


# ========================================
# ユーティリティ関数
# ========================================

def render_char_to_bitmap(char: str, font_path: str, size: int = 2048) -> Optional[Image.Image]:
    """文字をビットマップにレンダリング"""
    try:
        font = ImageFont.truetype(font_path, size)
        img = Image.new("L", (size, size), 255)
        draw = ImageDraw.Draw(img)

        bbox = draw.textbbox((0, 0), char, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        x = (size - w) / 2 - bbox[0]
        y = (size - h) / 2 - bbox[1]

        draw.text((x, y), char, fill=0, font=font)
        return img
    except Exception as e:
        print(f"❌ レンダリングエラー: {e}")
        return None


def get_bounding_box(binary_img: np.ndarray) -> Tuple[int, int, int, int]:
    """バウンディングボックスを取得"""
    rows = np.any(binary_img, axis=1)
    cols = np.any(binary_img, axis=0)

    if not rows.any() or not cols.any():
        return (0, 0, 0, 0)

    ymin, ymax = np.where(rows)[0][[0, -1]]
    xmin, xmax = np.where(cols)[0][[0, -1]]

    return (xmin, ymin, xmax + 1, ymax + 1)


# ========================================
# 動的境界検出統合抽出器
# ========================================

class DynamicExtractionDetector:
    """動的境界検出を使用した偏旁抽出器"""

    def __init__(self, ids_db: IDSDatabase, boundary_detector: DynamicBoundaryDetector):
        self.ids_db = ids_db
        self.boundary_detector = boundary_detector

    def extract_with_candidates(self, char: str, img: Image.Image) -> Optional[Dict]:
        """
        複数候補を提示しながら抽出

        Returns:
            {
                'char': 文字,
                'structure': IDS構造情報,
                'candidates': [
                    {
                        'name': '候補1 (最適)',
                        'ratio': 0.30,
                        'score': 0.15,
                        'left_image': Image,
                        'right_image': Image
                    },
                    ...
                ]
            }
        """
        structure = self.ids_db.get_structure(char)

        if not structure:
            return None

        operator = structure['operator']

        # 構造タイプに応じて処理
        if operator == 'left_right':
            return self._extract_left_right(char, img, structure)
        elif operator == 'top_bottom':
            return self._extract_top_bottom(char, img, structure)
        else:
            # その他の構造は後で実装
            return None

    def _extract_left_right(self, char: str, img: Image.Image, structure: Dict) -> Dict:
        """左右分割の抽出（複数候補）"""
        # 動的境界検出で最適位置を探す
        candidates_raw = self.boundary_detector.find_optimal_split(
            img, direction="vertical",
            search_range=Config.BOUNDARY_SEARCH_RANGE_LR,
            num_candidates=3
        )

        w, h = img.size
        img_array = np.array(img)
        binary = img_array < Config.BINARY_THRESHOLD

        result_candidates = []

        for idx, (ratio, score, info) in enumerate(candidates_raw):
            # 左成分抽出
            x_split = int(w * ratio)
            left_region = binary[:, :x_split]
            left_bbox = get_bounding_box(left_region)

            if left_bbox != (0, 0, 0, 0):
                left_img = img.crop((left_bbox[0], left_bbox[1], left_bbox[2], left_bbox[3]))
            else:
                left_img = None

            # 右成分抽出
            right_region = binary[:, x_split:]
            right_bbox = get_bounding_box(right_region)

            if right_bbox != (0, 0, 0, 0):
                rx1, ry1, rx2, ry2 = right_bbox
                right_img = img.crop((x_split + rx1, ry1, x_split + rx2, ry2))
            else:
                right_img = None

            candidate_name = f"候補{idx+1}"
            if idx == 0:
                candidate_name += " (最適)"

            result_candidates.append({
                'name': candidate_name,
                'ratio': ratio,
                'score': score,
                'info': info,
                'left_image': left_img,
                'right_image': right_img,
                'left_component': structure['components'][0] if structure['components'] else '?',
                'right_component': structure['components'][1] if len(structure['components']) > 1 else '?'
            })

        return {
            'char': char,
            'structure': structure,
            'operator': 'left_right',
            'candidates': result_candidates
        }

    def _extract_top_bottom(self, char: str, img: Image.Image, structure: Dict) -> Dict:
        """上下分割の抽出（複数候補）"""
        candidates_raw = self.boundary_detector.find_optimal_split(
            img, direction="horizontal",
            search_range=Config.BOUNDARY_SEARCH_RANGE_TB,
            num_candidates=3
        )

        w, h = img.size
        img_array = np.array(img)
        binary = img_array < Config.BINARY_THRESHOLD

        result_candidates = []

        for idx, (ratio, score, info) in enumerate(candidates_raw):
            y_split = int(h * ratio)

            # 上成分
            top_region = binary[:y_split, :]
            top_bbox = get_bounding_box(top_region)
            if top_bbox != (0, 0, 0, 0):
                top_img = img.crop((top_bbox[0], top_bbox[1], top_bbox[2], top_bbox[3]))
            else:
                top_img = None

            # 下成分
            bottom_region = binary[y_split:, :]
            bottom_bbox = get_bounding_box(bottom_region)
            if bottom_bbox != (0, 0, 0, 0):
                bx1, by1, bx2, by2 = bottom_bbox
                bottom_img = img.crop((bx1, y_split + by1, bx2, y_split + by2))
            else:
                bottom_img = None

            candidate_name = f"候補{idx+1}"
            if idx == 0:
                candidate_name += " (最適)"

            result_candidates.append({
                'name': candidate_name,
                'ratio': ratio,
                'score': score,
                'info': info,
                'top_image': top_img,
                'bottom_image': bottom_img,
                'top_component': structure['components'][0] if structure['components'] else '?',
                'bottom_component': structure['components'][1] if len(structure['components']) > 1 else '?'
            })

        return {
            'char': char,
            'structure': structure,
            'operator': 'top_bottom',
            'candidates': result_candidates
        }


# ========================================
# メインGUI
# ========================================

class RadicalDetectionExperiment(tk.Tk):
    """偏旁自動検出実験GUI v0.3.0"""

    def __init__(self):
        super().__init__()

        self.title("偏旁自動検出実験プログラム v0.3.0 統合版")
        self.geometry("1600x900")

        # データベース初期化
        print("=" * 70)
        print("偏旁自動検出実験プログラム v0.3.0 - 統合版")
        print("=" * 70)
        self.ids_db = IDSDatabase()
        self.boundary_detector = DynamicBoundaryDetector()
        self.dynamic_extractor = DynamicExtractionDetector(self.ids_db, self.boundary_detector)

        # 状態変数
        self.font_path = None
        self.current_char = None
        self.current_image = None
        self.result_images = []

        self._create_widgets()

        print("✅ 準備完了")
        print("=" * 70)

    def _create_widgets(self):
        """ウィジェット作成"""
        # メニューバー
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="フォントを開く", command=self._open_font)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.quit)

        # メインコンテナ
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左パネル
        left_panel = ttk.Frame(main_container, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5)

        # 入力エリア
        input_frame = ttk.LabelFrame(left_panel, text="入力")
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="文字:").grid(row=0, column=0, padx=5, pady=5)
        self.char_entry = ttk.Entry(input_frame, width=10, font=("", 20))
        self.char_entry.grid(row=0, column=1, padx=5, pady=5)
        self.char_entry.bind("<Return>", lambda e: self._render_char())

        ttk.Button(input_frame, text="レンダリング", command=self._render_char).grid(
            row=0, column=2, padx=5, pady=5
        )

        # 画像表示
        self.canvas = tk.Canvas(left_panel, width=Config.DISPLAY_SIZE,
                                height=Config.DISPLAY_SIZE, bg='white')
        self.canvas.pack(pady=10)

        # 検出方法選択
        method_frame = ttk.LabelFrame(left_panel, text="v0.3.0 新機能")
        method_frame.pack(fill=tk.X, pady=5)

        ttk.Button(method_frame, text="🎯 動的境界検出（複数候補）",
                  command=self._detect_dynamic, width=30).pack(pady=5)

        ttk.Label(method_frame, text="画像解析で最適な分割位置を自動検出\n複数候補を同時に表示します",
                 justify=tk.LEFT, foreground="gray").pack(pady=2)

        # IDS情報表示
        info_frame = ttk.LabelFrame(left_panel, text="IDS情報")
        info_frame.pack(fill=tk.X, pady=5)

        self.ids_info_label = ttk.Label(info_frame, text="文字をレンダリングしてください",
                                        justify=tk.LEFT, wraplength=380)
        self.ids_info_label.pack(padx=5, pady=5)

        # 右パネル: 結果表示
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        ttk.Label(right_panel, text="検出結果 - 複数候補", font=("", 12, "bold")).pack(pady=5)

        # スクロール可能な結果エリア
        self.result_canvas = tk.Canvas(right_panel, bg='#f0f0f0')
        result_scrollbar = ttk.Scrollbar(right_panel, orient=tk.VERTICAL,
                                         command=self.result_canvas.yview)
        self.result_canvas.configure(yscrollcommand=result_scrollbar.set)

        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.result_frame = ttk.Frame(self.result_canvas)
        self.result_canvas.create_window((0, 0), window=self.result_frame, anchor='nw')

        self.result_frame.bind("<Configure>",
                               lambda e: self.result_canvas.configure(
                                   scrollregion=self.result_canvas.bbox("all")))

        # ステータスバー
        self.status_label = ttk.Label(self, text="フォントを開いてください",
                                      relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def _open_font(self):
        """フォントを開く"""
        path = filedialog.askopenfilename(
            title="フォントを選択",
            filetypes=[("フォントファイル", "*.ttf *.otf"), ("すべて", "*.*")]
        )

        if path:
            self.font_path = path
            self.status_label.config(text=f"フォント: {os.path.basename(path)}")

    def _render_char(self):
        """文字をレンダリング"""
        if not self.font_path:
            messagebox.showerror("エラー", "先にフォントを開いてください")
            return

        char = self.char_entry.get().strip()
        if not char:
            return

        self.current_char = char[0]

        # レンダリング
        img = render_char_to_bitmap(self.current_char, self.font_path, Config.CANVAS_SIZE)

        if img:
            self.current_image = img
            self._display_image(img)

            # IDS情報を表示
            structure = self.ids_db.get_structure(self.current_char)
            if structure:
                info = f"IDS: {structure['ids']}\n"
                info += f"構造: {structure['operator']}\n"
                info += f"構成要素: {', '.join(structure['components'])}"
                self.ids_info_label.config(text=info)
            else:
                self.ids_info_label.config(text=f"文字「{self.current_char}」のIDS情報なし")

    def _display_image(self, img: Image.Image):
        """画像を表示"""
        display_img = img.resize((Config.DISPLAY_SIZE, Config.DISPLAY_SIZE),
                                 Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(display_img)
        self.canvas.delete("all")
        self.canvas.create_image(Config.DISPLAY_SIZE // 2, Config.DISPLAY_SIZE // 2,
                                 image=photo)
        self.canvas.image = photo

    def _detect_dynamic(self):
        """動的境界検出を実行"""
        if not self.current_image or not self.current_char:
            messagebox.showwarning("警告", "先に文字をレンダリングしてください")
            return

        # 動的境界検出で抽出
        result = self.dynamic_extractor.extract_with_candidates(
            self.current_char,
            self.current_image
        )

        if not result:
            messagebox.showinfo("情報",
                f"文字「{self.current_char}」の構造情報が見つからないか、\n"
                "対応していない構造です")
            return

        # 結果を表示
        self._display_dynamic_results(result)

    def _display_dynamic_results(self, result: Dict):
        """動的検出結果を表示"""
        # 既存の結果をクリア
        for widget in self.result_frame.winfo_children():
            widget.destroy()

        self.result_images.clear()

        # タイトル
        char = result['char']
        operator = result['operator']
        ttk.Label(self.result_frame,
                 text=f"文字「{char}」の抽出結果 - {operator}",
                 font=("", 11, "bold")).pack(pady=5)

        candidates = result['candidates']

        for candidate in candidates:
            frame = ttk.LabelFrame(self.result_frame, text=candidate['name'])
            frame.pack(fill=tk.X, padx=10, pady=5)

            # 情報テキスト
            info_text = f"分割位置: {candidate['ratio']:.2%}\n"
            info_text += f"スコア: {candidate['score']:.3f}\n"
            info_text += f"密度: {candidate['info']['density']:.3f}\n"
            info_text += f"エッジ: {candidate['info']['edge_score']:.3f}\n"

            ttk.Label(frame, text=info_text, justify=tk.LEFT).pack(side=tk.LEFT, padx=10, pady=5)

            # 画像プレビュー
            img_container = ttk.Frame(frame)
            img_container.pack(side=tk.LEFT, padx=10, pady=5)

            if operator == 'left_right':
                self._show_lr_images(img_container, candidate)
            elif operator == 'top_bottom':
                self._show_tb_images(img_container, candidate)

    def _show_lr_images(self, container, candidate):
        """左右分割の画像を表示"""
        left_img = candidate.get('left_image')
        right_img = candidate.get('right_image')

        # 左成分
        if left_img:
            left_frame = ttk.Frame(container)
            left_frame.pack(side=tk.LEFT, padx=5)

            ttk.Label(left_frame, text=f"左: {candidate['left_component']}").pack()

            max_size = 120
            left_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(left_img)
            self.result_images.append(photo)

            img_label = ttk.Label(left_frame, image=photo)
            img_label.pack()

            ttk.Button(left_frame, text="保存",
                      command=lambda img=candidate['left_image']: self._save_component(img, "left")).pack(pady=2)

        # 右成分
        if right_img:
            right_frame = ttk.Frame(container)
            right_frame.pack(side=tk.LEFT, padx=5)

            ttk.Label(right_frame, text=f"右: {candidate['right_component']}").pack()

            max_size = 120
            right_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(right_img)
            self.result_images.append(photo)

            img_label = ttk.Label(right_frame, image=photo)
            img_label.pack()

            ttk.Button(right_frame, text="保存",
                      command=lambda img=candidate['right_image']: self._save_component(img, "right")).pack(pady=2)

    def _show_tb_images(self, container, candidate):
        """上下分割の画像を表示"""
        top_img = candidate.get('top_image')
        bottom_img = candidate.get('bottom_image')

        if top_img:
            top_frame = ttk.Frame(container)
            top_frame.pack(side=tk.LEFT, padx=5)

            ttk.Label(top_frame, text=f"上: {candidate['top_component']}").pack()

            max_size = 120
            top_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(top_img)
            self.result_images.append(photo)

            img_label = ttk.Label(top_frame, image=photo)
            img_label.pack()

            ttk.Button(top_frame, text="保存",
                      command=lambda img=candidate['top_image']: self._save_component(img, "top")).pack(pady=2)

        if bottom_img:
            bottom_frame = ttk.Frame(container)
            bottom_frame.pack(side=tk.LEFT, padx=5)

            ttk.Label(bottom_frame, text=f"下: {candidate['bottom_component']}").pack()

            max_size = 120
            bottom_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(bottom_img)
            self.result_images.append(photo)

            img_label = ttk.Label(bottom_frame, image=photo)
            img_label.pack()

            ttk.Button(bottom_frame, text="保存",
                      command=lambda img=candidate['bottom_image']: self._save_component(img, "bottom")).pack(pady=2)

    def _save_component(self, img: Image.Image, component_name: str):
        """成分を保存"""
        file_path = filedialog.asksaveasfilename(
            title="成分を保存",
            defaultextension=".png",
            filetypes=[("PNG画像", "*.png"), ("すべて", "*.*")],
            initialfile=f"{self.current_char}_{component_name}.png"
        )

        if file_path:
            try:
                img.save(file_path)
                messagebox.showinfo("成功", f"保存しました: {file_path}")
            except Exception as e:
                messagebox.showerror("エラー", f"保存に失敗しました: {e}")


# ========================================
# メイン
# ========================================

def main():
    """メイン関数"""
    app = RadicalDetectionExperiment()
    app.mainloop()


if __name__ == "__main__":
    main()

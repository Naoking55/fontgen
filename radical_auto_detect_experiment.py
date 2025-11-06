#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
偏旁自動検出実験プログラム
Version: 0.1.0
Last Updated: 2025-11-06

実験機能:
1. 連結成分分析による偏旁分割
2. テンプレートマッチングによる偏旁検出
3. 複数文字からの共通部分抽出

実用レベルに達したら本体に統合予定
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageFont, ImageDraw, ImageTk, ImageOps, ImageFilter
import numpy as np
from scipy import ndimage
from typing import List, Tuple, Optional, Dict
import json

# ========================================
# 設定
# ========================================

class Config:
    """実験プログラム設定"""
    CANVAS_SIZE = 2048
    DISPLAY_SIZE = 400
    FONT_RENDER_SIZE = 2048

    # 連結成分分析パラメータ
    MIN_COMPONENT_SIZE = 100  # 最小成分サイズ（ピクセル数）
    BINARY_THRESHOLD = 200    # 2値化閾値

    # 分割方向の判定閾値
    VERTICAL_SPLIT_THRESHOLD = 0.4   # 縦分割判定（左右）
    HORIZONTAL_SPLIT_THRESHOLD = 0.3  # 横分割判定（上下）


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
        print(f"レンダリングエラー: {e}")
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


def crop_to_content(img: Image.Image, padding: int = 10) -> Image.Image:
    """コンテンツに合わせてクロップ"""
    # 2値化
    img_array = np.array(img)
    binary = img_array < 200

    # バウンディングボックス取得
    bbox = get_bounding_box(binary)

    if bbox == (0, 0, 0, 0):
        return img

    # パディング追加
    x1 = max(0, bbox[0] - padding)
    y1 = max(0, bbox[1] - padding)
    x2 = min(img.width, bbox[2] + padding)
    y2 = min(img.height, bbox[3] + padding)

    return img.crop((x1, y1, x2, y2))


# ========================================
# 連結成分分析
# ========================================

class ConnectedComponentAnalyzer:
    """連結成分分析による偏旁分割"""

    def __init__(self, binary_threshold: int = 200, min_size: int = 100):
        self.binary_threshold = binary_threshold
        self.min_size = min_size

    def analyze(self, img: Image.Image) -> List[Dict]:
        """
        連結成分分析を実行

        Returns:
            成分のリスト [{image, bbox, size, position}, ...]
        """
        # グレースケール配列に変換
        img_array = np.array(img)

        # 2値化（黒=1, 白=0）
        binary = img_array < self.binary_threshold

        # ラベリング
        labeled, num_features = ndimage.label(binary)

        components = []

        for i in range(1, num_features + 1):
            # 成分マスク
            component_mask = labeled == i

            # サイズチェック
            size = np.sum(component_mask)
            if size < self.min_size:
                continue

            # バウンディングボックス
            bbox = get_bounding_box(component_mask)
            if bbox == (0, 0, 0, 0):
                continue

            x1, y1, x2, y2 = bbox

            # 成分画像を抽出
            component_img = np.ones_like(img_array) * 255
            component_img[component_mask] = img_array[component_mask]
            component_pil = Image.fromarray(component_img).crop(bbox)

            # 位置を判定（左・右・上・下）
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            img_center_x = img.width / 2
            img_center_y = img.height / 2

            position = self._determine_position(
                center_x, center_y, img_center_x, img_center_y,
                bbox, img.width, img.height
            )

            components.append({
                'image': component_pil,
                'bbox': bbox,
                'size': size,
                'position': position,
                'center': (center_x, center_y)
            })

        return components

    def _determine_position(self, cx, cy, img_cx, img_cy, bbox, w, h):
        """成分の位置を判定"""
        x1, y1, x2, y2 = bbox

        # 左右判定
        if cx < img_cx * 0.4:
            if cy > img_cy * 1.5:
                return 'left_bottom'  # 左下
            return 'left'
        elif cx > img_cx * 1.6:
            return 'right'
        # 上下判定
        elif cy < img_cy * 0.4:
            return 'top'
        elif cy > img_cy * 1.6:
            return 'bottom'
        else:
            return 'center'

    def suggest_split_type(self, components: List[Dict]) -> str:
        """成分から偏旁タイプを推定"""
        if len(components) < 2:
            return 'none'

        positions = [c['position'] for c in components]

        # 左右分割
        if 'left' in positions and 'right' in positions:
            return 'left_right'
        # 上下分割
        elif 'top' in positions and 'bottom' in positions:
            return 'top_bottom'
        # 左下
        elif 'left_bottom' in positions:
            return 'left_bottom'
        # 囲み
        elif len(components) >= 3:
            return 'frame'

        return 'unknown'


# ========================================
# テンプレートマッチング
# ========================================

class TemplateMatchingDetector:
    """テンプレートマッチングによる偏旁検出"""

    def __init__(self, template_dir: str = "assets/parts"):
        self.template_dir = template_dir
        self.templates = {}
        self._load_templates()

    def _load_templates(self):
        """テンプレート読み込み"""
        if not os.path.exists(self.template_dir):
            return

        for filename in os.listdir(self.template_dir):
            if filename.endswith('.png'):
                path = os.path.join(self.template_dir, filename)
                try:
                    img = Image.open(path).convert('L')
                    name = os.path.splitext(filename)[0]
                    self.templates[name] = img
                except Exception as e:
                    print(f"テンプレート読み込みエラー {filename}: {e}")

    def match(self, target_img: Image.Image, template_name: str,
              scale_range: Tuple[float, float] = (0.5, 1.5)) -> Optional[Dict]:
        """
        テンプレートマッチング実行

        Returns:
            {score, position, scale} or None
        """
        if template_name not in self.templates:
            return None

        template = self.templates[template_name]
        target_array = np.array(target_img)

        best_match = None
        best_score = 0

        # スケールを変えながらマッチング
        for scale in np.arange(scale_range[0], scale_range[1], 0.1):
            # テンプレートをリサイズ
            new_size = (
                int(template.width * scale),
                int(template.height * scale)
            )
            if new_size[0] <= 0 or new_size[1] <= 0:
                continue
            if new_size[0] > target_img.width or new_size[1] > target_img.height:
                continue

            scaled_template = template.resize(new_size, Image.Resampling.LANCZOS)
            template_array = np.array(scaled_template)

            # 正規化相互相関
            score, pos = self._ncc_match(target_array, template_array)

            if score > best_score:
                best_score = score
                best_match = {
                    'score': score,
                    'position': pos,
                    'scale': scale,
                    'template_name': template_name
                }

        return best_match if best_score > 0.7 else None

    def _ncc_match(self, target: np.ndarray, template: np.ndarray) -> Tuple[float, Tuple[int, int]]:
        """正規化相互相関マッチング"""
        from scipy.signal import correlate2d

        # 正規化
        target_norm = (target - target.mean()) / (target.std() + 1e-8)
        template_norm = (template - template.mean()) / (template.std() + 1e-8)

        # 相関計算
        corr = correlate2d(target_norm, template_norm, mode='valid')

        # 最大値の位置とスコア
        max_pos = np.unravel_index(np.argmax(corr), corr.shape)
        max_score = corr[max_pos] / (template.size)

        return (float(max_score), (int(max_pos[1]), int(max_pos[0])))


# ========================================
# 複数文字からの共通部分抽出
# ========================================

class CommonPartExtractor:
    """複数文字からの共通部分抽出"""

    def extract_common_part(self, images: List[Image.Image],
                           threshold: float = 0.7) -> Optional[Image.Image]:
        """
        複数画像から共通部分を抽出

        Args:
            images: 画像リスト
            threshold: 共通判定閾値（0.0-1.0）

        Returns:
            共通部分の画像
        """
        if len(images) < 2:
            return None

        # すべての画像を同じサイズにリサイズ
        size = images[0].size
        resized = [img.resize(size, Image.Resampling.LANCZOS) for img in images]

        # 配列に変換
        arrays = [np.array(img) for img in resized]

        # 2値化
        binaries = [arr < 200 for arr in arrays]

        # 共通部分を計算（すべての画像で黒いピクセル）
        common = np.ones_like(binaries[0], dtype=bool)
        for binary in binaries:
            common = common & binary

        # 共通度が閾値以下の場合は失敗
        common_ratio = np.sum(common) / np.sum(binaries[0])
        if common_ratio < threshold:
            return None

        # 画像に変換
        result = np.ones_like(arrays[0]) * 255
        result[common] = 0

        return Image.fromarray(result)


# ========================================
# 実験用GUI
# ========================================

class RadicalDetectionExperimentGUI:
    """偏旁自動検出実験GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("偏旁自動検出実験プログラム v0.1.0")
        self.root.geometry("1200x800")

        self.font_path = None
        self.current_char = None
        self.current_image = None
        self.components = []

        self.analyzer = ConnectedComponentAnalyzer()
        self.template_matcher = TemplateMatchingDetector()
        self.common_extractor = CommonPartExtractor()

        self._setup_ui()

    def _setup_ui(self):
        """UI構築"""
        # メニュー
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="フォントを開く", command=self._load_font)

        # メインフレーム
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左パネル: 入力
        left_panel = tk.LabelFrame(main_frame, text="入力", padx=10, pady=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 文字入力
        input_frame = tk.Frame(left_panel)
        input_frame.pack(fill=tk.X, pady=5)

        tk.Label(input_frame, text="文字:").pack(side=tk.LEFT)
        self.char_entry = tk.Entry(input_frame, width=10, font=("", 16))
        self.char_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="レンダリング", command=self._render_char).pack(side=tk.LEFT)

        # 元画像表示
        self.original_canvas = tk.Canvas(left_panel, width=400, height=400, bg='white')
        self.original_canvas.pack(pady=10)

        # パラメータ
        param_frame = tk.LabelFrame(left_panel, text="パラメータ", padx=10, pady=10)
        param_frame.pack(fill=tk.X, pady=5)

        tk.Label(param_frame, text="2値化閾値:").grid(row=0, column=0, sticky='w')
        self.threshold_var = tk.IntVar(value=200)
        tk.Scale(param_frame, from_=0, to=255, orient=tk.HORIZONTAL,
                variable=self.threshold_var, length=200).grid(row=0, column=1)

        tk.Label(param_frame, text="最小サイズ:").grid(row=1, column=0, sticky='w')
        self.min_size_var = tk.IntVar(value=100)
        tk.Scale(param_frame, from_=10, to=1000, orient=tk.HORIZONTAL,
                variable=self.min_size_var, length=200).grid(row=1, column=1)

        # 実行ボタン
        tk.Button(left_panel, text="連結成分分析を実行",
                 command=self._run_analysis, font=("", 12, "bold")).pack(pady=10)

        # 右パネル: 結果
        right_panel = tk.LabelFrame(main_frame, text="検出結果", padx=10, pady=10)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 結果表示エリア
        self.result_text = tk.Text(right_panel, height=5, width=40)
        self.result_text.pack(fill=tk.X, pady=5)

        # 成分表示
        self.components_frame = tk.Frame(right_panel)
        self.components_frame.pack(fill=tk.BOTH, expand=True)

        # スクロール可能
        canvas_scroll = tk.Canvas(self.components_frame)
        scrollbar = tk.Scrollbar(self.components_frame, orient="vertical",
                                command=canvas_scroll.yview)
        self.scrollable_frame = tk.Frame(canvas_scroll)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
        )

        canvas_scroll.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)

        canvas_scroll.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _load_font(self):
        """フォント読み込み"""
        path = filedialog.askopenfilename(
            title='フォントファイルを選択',
            filetypes=[
                ('TrueType Font', '*.ttf'),
                ('OpenType Font', '*.otf'),
                ('All Files', '*.*')
            ]
        )
        if path:
            self.font_path = path
            messagebox.showinfo("成功", f"フォントを読み込みました:\n{os.path.basename(path)}")

    def _render_char(self):
        """文字をレンダリング"""
        if not self.font_path:
            messagebox.showwarning("警告", "先にフォントを読み込んでください")
            return

        char = self.char_entry.get()
        if not char:
            messagebox.showwarning("警告", "文字を入力してください")
            return

        self.current_char = char
        self.current_image = render_char_to_bitmap(char, self.font_path)

        if self.current_image:
            self._display_original()
        else:
            messagebox.showerror("エラー", "レンダリングに失敗しました")

    def _display_original(self):
        """元画像を表示"""
        if not self.current_image:
            return

        # 400x400に縮小
        display_img = self.current_image.resize((400, 400), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(display_img)

        self.original_canvas.delete("all")
        self.original_canvas.create_image(200, 200, image=photo)
        self.original_canvas.image = photo

    def _run_analysis(self):
        """連結成分分析を実行"""
        if not self.current_image:
            messagebox.showwarning("警告", "先に文字をレンダリングしてください")
            return

        # パラメータ更新
        self.analyzer.binary_threshold = self.threshold_var.get()
        self.analyzer.min_size = self.min_size_var.get()

        # 分析実行
        self.components = self.analyzer.analyze(self.current_image)

        # 結果表示
        self._display_results()

    def _display_results(self):
        """結果を表示"""
        # テキスト結果
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert('1.0', f"検出成分数: {len(self.components)}\n")

        if len(self.components) > 0:
            split_type = self.analyzer.suggest_split_type(self.components)
            self.result_text.insert(tk.END, f"推定偏旁タイプ: {split_type}\n\n")

            for i, comp in enumerate(self.components):
                self.result_text.insert(tk.END,
                    f"成分{i+1}: {comp['position']}, "
                    f"サイズ={comp['size']}px\n"
                )

        # 成分画像表示
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        for i, comp in enumerate(self.components):
            frame = tk.Frame(self.scrollable_frame, relief=tk.RAISED, borderwidth=2)
            frame.pack(fill=tk.X, pady=5, padx=5)

            # ラベル
            tk.Label(frame, text=f"成分{i+1}: {comp['position']}",
                    font=("", 10, "bold")).pack()

            # 画像
            img = comp['image']
            # 最大200x200に縮小
            max_size = 200
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            display_img = img.resize(new_size, Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(display_img)
            label = tk.Label(frame, image=photo)
            label.image = photo
            label.pack()

            # 保存ボタン
            tk.Button(frame, text="この成分を保存",
                     command=lambda c=comp: self._save_component(c)).pack(pady=5)

    def _save_component(self, component):
        """成分を保存"""
        path = filedialog.asksaveasfilename(
            title='成分を保存',
            defaultextension='.png',
            initialfile=f'{self.current_char}_{component["position"]}.png',
            filetypes=[('PNG Image', '*.png')]
        )

        if path:
            # クロップして保存
            cropped = crop_to_content(component['image'])
            cropped.save(path, 'PNG')
            messagebox.showinfo("成功", f"保存しました:\n{path}")


# ========================================
# メイン
# ========================================

def main():
    root = tk.Tk()
    app = RadicalDetectionExperimentGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

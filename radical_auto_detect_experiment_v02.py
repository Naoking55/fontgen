#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
偏旁自動検出実験プログラム v0.2.0
Version: 0.2.0
Last Updated: 2025-11-06

新機能:
1. Unicode IDS (Ideographic Description Sequences) データベースを使用した構造分析
2. 辞書ベースの偏旁検出（部首データベース参照）
3. 複数文字から共通偏旁を抽出する改良版アルゴリズム
4. 旧字体・新字体の対応

実験機能（v0.1.0から継承）:
1. 連結成分分析による偏旁分割
2. テンプレートマッチングによる偏旁検出
3. 複数文字からの共通部分抽出

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
    MIN_COMPONENT_SIZE = 100  # 最小成分サイズ（ピクセル数）
    BINARY_THRESHOLD = 200    # 2値化閾値

    # 分割方向の判定閾値
    VERTICAL_SPLIT_THRESHOLD = 0.4   # 縦分割判定（左右）
    HORIZONTAL_SPLIT_THRESHOLD = 0.3  # 横分割判定（上下）

    # IDSデータキャッシュ
    IDS_CACHE_FILE = "ids_cache.json"
    IDS_SOURCE_URL = "https://raw.githubusercontent.com/cjkvi/cjkvi-ids/master/ids.txt"


# ========================================
# IDS (Ideographic Description Sequences) パーサー
# ========================================

class IDSDatabase:
    """IDS (Ideographic Description Sequences) データベース"""

    # IDS演算子
    IDS_OPERATORS = {
        '\u2FF0': 'left_right',      # ⿰ 左右配置
        '\u2FF1': 'top_bottom',      # ⿱ 上下配置
        '\u2FF2': 'top_lr',          # ⿲ 上から左右配置
        '\u2FF3': 'left_tb',         # ⿳ 左から上下配置
        '\u2FF4': 'surround_full',   # ⿴ 全包囲
        '\u2FF5': 'surround_above',  # ⿵ 上三方包囲
        '\u2FF6': 'surround_below',  # ⿶ 下三方包囲
        '\u2FF7': 'surround_left',   # ⿷ 左三方包囲
        '\u2FF8': 'surround_upper_left',  # ⿸ 左上包囲
        '\u2FF9': 'surround_upper_right', # ⿹ 右上包囲
        '\u2FFA': 'surround_lower_left',  # ⿺ 左下包囲
        '\u2FFB': 'overlay',         # ⿻ 重ね
    }

    def __init__(self):
        self.ids_data: Dict[str, str] = {}  # char -> IDS
        self.radical_chars: Dict[int, str] = {}  # radical_number -> char
        self._load_or_download()

    def _load_or_download(self):
        """IDSデータをロードまたはダウンロード"""
        if os.path.exists(Config.IDS_CACHE_FILE):
            try:
                with open(Config.IDS_CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.ids_data = json.load(f)
                print(f"IDSデータをキャッシュから読み込みました: {len(self.ids_data)} エントリ")
                return
            except Exception as e:
                print(f"キャッシュ読み込みエラー: {e}")

        # ダウンロードして解析
        self._download_and_parse()

    def _download_and_parse(self):
        """IDSデータをダウンロードして解析"""
        print("IDSデータをダウンロード中...")
        try:
            with urllib.request.urlopen(Config.IDS_SOURCE_URL, timeout=30) as response:
                content = response.read().decode('utf-8')

            # 解析
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split('\t')
                if len(parts) >= 3:
                    # U+XXXX, character, IDS
                    char = parts[1]
                    ids = parts[2]
                    self.ids_data[char] = ids

            # キャッシュに保存
            with open(Config.IDS_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.ids_data, f, ensure_ascii=False, indent=2)

            print(f"IDSデータを取得しました: {len(self.ids_data)} エントリ")

        except Exception as e:
            print(f"IDSダウンロードエラー: {e}")
            print("オフラインモードで動作します")

    def get_structure(self, char: str) -> Optional[Dict]:
        """
        文字の構造情報を取得

        Returns:
            {
                'char': 文字,
                'ids': IDS文字列,
                'operator': 構造タイプ (left_right, top_bottom, etc.),
                'components': 構成要素のリスト
            }
        """
        if char not in self.ids_data:
            return None

        ids = self.ids_data[char]

        # 最初のIDS演算子を探す
        operator = None
        operator_char = None
        for op_char, op_type in self.IDS_OPERATORS.items():
            if op_char in ids:
                operator = op_type
                operator_char = op_char
                break

        if not operator:
            return None

        # 構成要素を抽出
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
        """IDS文字列から構成要素を抽出"""
        components = []
        i = 0
        while i < len(ids_str):
            char = ids_str[i]

            # 入れ子のIDS演算子がある場合
            if char in self.IDS_OPERATORS:
                # 再帰的に処理が必要だが、簡易版では次の2文字を取得
                if i + 2 < len(ids_str):
                    components.append(ids_str[i:i+3])
                    i += 3
                else:
                    i += 1
            else:
                components.append(char)
                i += 1

        return components

    def find_characters_with_component(self, component: str, max_results: int = 100) -> List[str]:
        """指定した構成要素を含む文字を検索"""
        results = []
        for char, ids in self.ids_data.items():
            if component in ids:
                results.append(char)
                if len(results) >= max_results:
                    break
        return results


# ========================================
# 康熙部首データベース
# ========================================

class KangxiRadicalDatabase:
    """康熙部首データベース"""

    # 康熙214部首（簡略版）
    KANGXI_RADICALS = {
        1: "一", 2: "丨", 3: "丶", 4: "丿", 5: "乙",
        6: "亅", 7: "二", 8: "亠", 9: "人", 10: "儿",
        11: "入", 12: "八", 13: "冂", 14: "冖", 15: "冫",
        16: "几", 17: "凵", 18: "刀", 19: "力", 20: "勹",
        21: "匕", 22: "匚", 23: "匸", 24: "十", 25: "卜",
        26: "卩", 27: "厂", 28: "厶", 29: "又", 30: "口",
        31: "囗", 32: "土", 33: "士", 34: "夂", 35: "夊",
        36: "夕", 37: "大", 38: "女", 39: "子", 40: "宀",
        41: "寸", 42: "小", 43: "尢", 44: "尸", 45: "屮",
        46: "山", 47: "巛", 48: "工", 49: "己", 50: "巾",
        51: "干", 52: "幺", 53: "广", 54: "廴", 55: "廾",
        56: "弋", 57: "弓", 58: "彐", 59: "彡", 60: "彳",
        61: "心", 62: "戈", 63: "戶", 64: "手", 65: "支",
        66: "攴", 67: "文", 68: "斗", 69: "斤", 70: "方",
        71: "无", 72: "日", 73: "曰", 74: "月", 75: "木",
        76: "欠", 77: "止", 78: "歹", 79: "殳", 80: "毋",
        81: "比", 82: "毛", 83: "氏", 84: "气", 85: "水",
        86: "火", 87: "爪", 88: "父", 89: "爻", 90: "爿",
        91: "片", 92: "牙", 93: "牛", 94: "犬", 95: "玄",
        96: "玉", 97: "瓜", 98: "瓦", 99: "甘", 100: "生",
        101: "用", 102: "田", 103: "疋", 104: "疒", 105: "癶",
        106: "白", 107: "皮", 108: "皿", 109: "目", 110: "矛",
        111: "矢", 112: "石", 113: "示", 114: "禸", 115: "禾",
        116: "穴", 117: "立", 118: "竹", 119: "米", 120: "糸",
        121: "缶", 122: "网", 123: "羊", 124: "羽", 125: "老",
        126: "而", 127: "耒", 128: "耳", 129: "聿", 130: "肉",
        131: "臣", 132: "自", 133: "至", 134: "臼", 135: "舌",
        136: "舛", 137: "舟", 138: "艮", 139: "色", 140: "艸",
        141: "虍", 142: "虫", 143: "血", 144: "行", 145: "衣",
        146: "襾", 147: "見", 148: "角", 149: "言", 150: "谷",
        151: "豆", 152: "豕", 153: "豸", 154: "貝", 155: "赤",
        156: "走", 157: "足", 158: "身", 159: "車", 160: "辛",
        161: "辰", 162: "辵", 163: "邑", 164: "酉", 165: "釆",
        166: "里", 167: "金", 168: "長", 169: "門", 170: "阜",
        171: "隶", 172: "隹", 173: "雨", 174: "青", 175: "非",
        176: "面", 177: "革", 178: "韋", 179: "韭", 180: "音",
        181: "頁", 182: "風", 183: "飛", 184: "食", 185: "首",
        186: "香", 187: "馬", 188: "骨", 189: "高", 190: "髟",
        191: "鬥", 192: "鬯", 193: "鬲", 194: "鬼", 195: "魚",
        196: "鳥", 197: "鹵", 198: "鹿", 199: "麥", 200: "麻",
        201: "黃", 202: "黍", 203: "黑", 204: "黹", 205: "黽",
        206: "鼎", 207: "鼓", 208: "鼠", 209: "鼻", 210: "齊",
        211: "齒", 212: "龍", 213: "龜", 214: "龠",
    }

    # よく使われる偏旁の別名・異体字
    RADICAL_VARIANTS = {
        "氵": 85,   # さんずい (水)
        "扌": 64,   # てへん (手)
        "忙": 61,   # りっしんべん (心)
        "艹": 140,  # くさかんむり (艸)
        "辶": 162,  # しんにょう (辵)
        "礻": 113,  # しめすへん (示)
        "訁": 149,  # ごんべん (言)
        "釒": 167,  # かねへん (金)
        "飠": 184,  # しょくへん (食)
        "阝": 170,  # こざとへん (阜)
        "犭": 94,   # けものへん (犬)
        "⺼": 130,  # にくづき (肉)
    }

    def __init__(self):
        self.radical_to_chars: Dict[int, List[str]] = defaultdict(list)
        self._build_reverse_index()

    def _build_reverse_index(self):
        """部首から文字への逆引きインデックスを構築（簡略版）"""
        # 実際にはUnihanデータベースのkRSUnicodeフィールドを使用すべき
        # ここでは簡略版として空実装
        pass

    def get_radical_char(self, radical_num: int) -> Optional[str]:
        """部首番号から部首文字を取得"""
        return self.KANGXI_RADICALS.get(radical_num)

    def find_radical_number(self, char: str) -> Optional[int]:
        """文字から部首番号を取得（異体字対応）"""
        if char in self.RADICAL_VARIANTS:
            return self.RADICAL_VARIANTS[char]

        # 康熙部首の直接検索
        for num, radical in self.KANGXI_RADICALS.items():
            if radical == char:
                return num

        return None


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
    img_array = np.array(img)
    binary = img_array < 200
    bbox = get_bounding_box(binary)

    if bbox == (0, 0, 0, 0):
        return img

    x1 = max(0, bbox[0] - padding)
    y1 = max(0, bbox[1] - padding)
    x2 = min(img.width, bbox[2] + padding)
    y2 = min(img.height, bbox[3] + padding)

    return img.crop((x1, y1, x2, y2))


# ========================================
# 辞書ベース偏旁検出器
# ========================================

class DictionaryBasedDetector:
    """辞書ベースの偏旁検出器"""

    def __init__(self, ids_db: IDSDatabase, radical_db: KangxiRadicalDatabase):
        self.ids_db = ids_db
        self.radical_db = radical_db

    def detect_structure(self, char: str) -> Optional[Dict]:
        """
        文字の構造を辞書から検出

        Returns:
            {
                'structure_type': 構造タイプ,
                'components': 構成要素リスト,
                'extraction_guide': 抽出ガイド
            }
        """
        structure = self.ids_db.get_structure(char)

        if not structure:
            return None

        operator = structure['operator']
        components = structure['components']

        # 抽出ガイドを生成
        guide = self._create_extraction_guide(operator, components)

        return {
            'structure_type': operator,
            'components': components,
            'extraction_guide': guide,
            'ids': structure['ids']
        }

    def _create_extraction_guide(self, operator: str, components: List[str]) -> Dict:
        """構造タイプから抽出ガイドを生成"""
        guide = {
            'type': operator,
            'regions': []
        }

        if operator == 'left_right':
            # 左右分割
            guide['regions'] = [
                {'name': 'left', 'component': components[0] if components else '?', 'bbox': 'left_half'},
                {'name': 'right', 'component': components[1] if len(components) > 1 else '?', 'bbox': 'right_half'}
            ]
        elif operator == 'top_bottom':
            # 上下分割
            guide['regions'] = [
                {'name': 'top', 'component': components[0] if components else '?', 'bbox': 'top_half'},
                {'name': 'bottom', 'component': components[1] if len(components) > 1 else '?', 'bbox': 'bottom_half'}
            ]
        elif operator in ['surround_above', 'surround_full']:
            # 包囲構造（冠や門）
            guide['regions'] = [
                {'name': 'surround', 'component': components[0] if components else '?', 'bbox': 'frame'},
                {'name': 'inner', 'component': components[1] if len(components) > 1 else '?', 'bbox': 'center'}
            ]
        elif operator == 'surround_upper_left':
            # 左上包囲（まだれなど）
            guide['regions'] = [
                {'name': 'surround', 'component': components[0] if components else '?', 'bbox': 'upper_left_frame'},
                {'name': 'inner', 'component': components[1] if len(components) > 1 else '?', 'bbox': 'lower_right'}
            ]

        return guide

    def extract_by_guide(self, img: Image.Image, guide: Dict, binary_threshold: int = 200) -> List[Dict]:
        """
        抽出ガイドに基づいて画像から偏旁を抽出

        Returns:
            [{'name': 領域名, 'image': 抽出画像, 'component': 構成要素}, ...]
        """
        results = []
        img_array = np.array(img)
        binary = img_array < binary_threshold

        w, h = img.width, img.height

        for region in guide.get('regions', []):
            bbox_type = region.get('bbox')

            # bbox_typeに基づいて領域を切り出し
            if bbox_type == 'left_half':
                x1, y1, x2, y2 = 0, 0, w // 2 + w // 10, h
            elif bbox_type == 'right_half':
                x1, y1, x2, y2 = w // 2 - w // 10, 0, w, h
            elif bbox_type == 'top_half':
                x1, y1, x2, y2 = 0, 0, w, h // 2 + h // 10
            elif bbox_type == 'bottom_half':
                x1, y1, x2, y2 = 0, h // 2 - h // 10, w, h
            elif bbox_type == 'upper_left_frame':
                # 上部と左側のL字型領域を抽出（簡易版）
                x1, y1, x2, y2 = 0, 0, w, h // 2
            elif bbox_type == 'lower_right':
                x1, y1, x2, y2 = w // 4, h // 3, w, h
            else:
                continue

            # 範囲チェック
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            # 領域を抽出
            region_binary = binary[y1:y2, x1:x2]

            # コンテンツのバウンディングボックスを取得
            region_bbox = get_bounding_box(region_binary)

            if region_bbox != (0, 0, 0, 0):
                rx1, ry1, rx2, ry2 = region_bbox
                # 元画像の座標系に変換
                abs_x1 = x1 + rx1
                abs_y1 = y1 + ry1
                abs_x2 = x1 + rx2
                abs_y2 = y1 + ry2

                # 画像を切り出し
                extracted = img.crop((abs_x1, abs_y1, abs_x2, abs_y2))

                results.append({
                    'name': region['name'],
                    'image': extracted,
                    'component': region.get('component', '?'),
                    'bbox': (abs_x1, abs_y1, abs_x2, abs_y2)
                })

        return results


# ========================================
# 複数文字からの共通偏旁抽出（改良版）
# ========================================

class ImprovedCommonPartExtractor:
    """改良版: 複数文字からの共通偏旁抽出"""

    def __init__(self, ids_db: IDSDatabase):
        self.ids_db = ids_db

    def find_common_radical(self, chars: List[str]) -> Optional[str]:
        """複数の文字から共通の構成要素を見つける"""
        if len(chars) < 2:
            return None

        # 各文字の構成要素を取得
        all_components = []
        for char in chars:
            structure = self.ids_db.get_structure(char)
            if structure:
                all_components.append(set(structure['components']))
            else:
                # IDSデータがない場合は処理できない
                return None

        if not all_components:
            return None

        # 共通集合を計算
        common = all_components[0]
        for components in all_components[1:]:
            common = common & components

        if common:
            # 最も頻出する構成要素を返す
            return list(common)[0]

        return None

    def extract_common_part_images(self, chars: List[str], font_path: str,
                                   detector: 'DictionaryBasedDetector') -> List[Dict]:
        """
        複数の文字から共通偏旁の画像を抽出

        Returns:
            [{'char': 文字, 'common_part': 共通部分名, 'image': 抽出画像}, ...]
        """
        # 共通構成要素を見つける
        common_component = self.find_common_radical(chars)

        if not common_component:
            return []

        results = []

        for char in chars:
            # 文字をレンダリング
            img = render_char_to_bitmap(char, font_path, Config.FONT_RENDER_SIZE)
            if not img:
                continue

            # 構造情報を取得
            structure_info = detector.detect_structure(char)
            if not structure_info:
                continue

            # 抽出ガイドに基づいて抽出
            extracted = detector.extract_by_guide(img, structure_info['extraction_guide'])

            # 共通構成要素に対応する画像を探す
            for part in extracted:
                if part['component'] == common_component:
                    results.append({
                        'char': char,
                        'common_part': common_component,
                        'image': part['image'],
                        'region': part['name']
                    })
                    break

        return results


# ========================================
# 連結成分分析（v0.1.0から継承）
# ========================================

class ConnectedComponentAnalyzer:
    """連結成分分析による偏旁分割"""

    def __init__(self, binary_threshold: int = 200, min_size: int = 100):
        self.binary_threshold = binary_threshold
        self.min_size = min_size

    def analyze(self, img: Image.Image) -> List[Dict]:
        """連結成分分析を実行"""
        img_array = np.array(img)
        binary = img_array < self.binary_threshold
        labeled, num_features = ndimage.label(binary)

        components = []

        for i in range(1, num_features + 1):
            component_mask = labeled == i
            size = np.sum(component_mask)

            if size < self.min_size:
                continue

            bbox = get_bounding_box(component_mask)
            if bbox == (0, 0, 0, 0):
                continue

            x1, y1, x2, y2 = bbox

            # 成分画像を抽出
            component_img = np.ones_like(img_array) * 255
            component_img[component_mask] = img_array[component_mask]
            component_pil = Image.fromarray(component_img).crop(bbox)

            # 位置を判定
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
        if cx < img_cx * 0.4:
            if cy > img_cy * 1.5:
                return 'left_bottom'
            return 'left'
        elif cx > img_cx * 1.6:
            return 'right'
        elif cy < img_cy * 0.4:
            return 'top'
        elif cy > img_cy * 1.6:
            return 'bottom'
        else:
            return 'center'


# ========================================
# メインGUI
# ========================================

class RadicalDetectionExperiment(tk.Tk):
    """偏旁自動検出実験GUI v0.2.0"""

    def __init__(self):
        super().__init__()

        self.title("偏旁自動検出実験プログラム v0.2.0")
        self.geometry("1400x900")

        # データベース初期化
        print("データベースを初期化中...")
        self.ids_db = IDSDatabase()
        self.radical_db = KangxiRadicalDatabase()
        self.dict_detector = DictionaryBasedDetector(self.ids_db, self.radical_db)
        self.component_analyzer = ConnectedComponentAnalyzer()
        self.common_extractor = ImprovedCommonPartExtractor(self.ids_db)

        # 状態変数
        self.font_path = None
        self.current_char = None
        self.current_image = None
        self.result_images = []

        self._create_widgets()

        print("準備完了")

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

        # 左パネル: 入力と表示
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

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
        method_frame = ttk.LabelFrame(left_panel, text="検出方法")
        method_frame.pack(fill=tk.X, pady=5)

        ttk.Button(method_frame, text="🔍 辞書ベース検出",
                  command=self._detect_by_dictionary, width=25).pack(pady=5)

        ttk.Button(method_frame, text="🧩 連結成分分析",
                  command=self._detect_by_connected_components, width=25).pack(pady=5)

        # 複数文字入力フレーム
        multi_frame = ttk.LabelFrame(left_panel, text="複数文字から共通偏旁抽出")
        multi_frame.pack(fill=tk.X, pady=5)

        ttk.Label(multi_frame, text="文字列（例: 海江河）:").pack(pady=2)
        self.multi_char_entry = ttk.Entry(multi_frame, width=30)
        self.multi_char_entry.pack(pady=2)

        ttk.Button(multi_frame, text="共通偏旁を抽出",
                  command=self._extract_common_radical).pack(pady=5)

        # パラメータ
        param_frame = ttk.LabelFrame(left_panel, text="パラメータ")
        param_frame.pack(fill=tk.X, pady=5)

        ttk.Label(param_frame, text="2値化閾値:").grid(row=0, column=0, padx=5, pady=2)
        self.threshold_var = tk.IntVar(value=200)
        ttk.Scale(param_frame, from_=100, to=250, variable=self.threshold_var,
                 orient=tk.HORIZONTAL, length=200).grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(param_frame, textvariable=self.threshold_var).grid(row=0, column=2, padx=5, pady=2)

        ttk.Label(param_frame, text="最小サイズ:").grid(row=1, column=0, padx=5, pady=2)
        self.min_size_var = tk.IntVar(value=100)
        ttk.Scale(param_frame, from_=50, to=500, variable=self.min_size_var,
                 orient=tk.HORIZONTAL, length=200).grid(row=1, column=1, padx=5, pady=2)
        ttk.Label(param_frame, textvariable=self.min_size_var).grid(row=1, column=2, padx=5, pady=2)

        # 右パネル: 結果表示
        right_panel = ttk.Frame(main_container, width=600)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        ttk.Label(right_panel, text="検出結果", font=("", 12, "bold")).pack(pady=5)

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

        self.current_char = char[0]  # 最初の1文字

        # レンダリング
        img = render_char_to_bitmap(self.current_char, self.font_path, Config.CANVAS_SIZE)

        if img:
            self.current_image = img
            self._display_image(img)

            # 辞書情報を表示
            structure = self.ids_db.get_structure(self.current_char)
            if structure:
                info = f"IDS: {structure['ids']}\n構造: {structure['operator']}\n構成要素: {', '.join(structure['components'])}"
                self.status_label.config(text=info)
            else:
                self.status_label.config(text=f"文字「{self.current_char}」のIDS情報なし")

    def _display_image(self, img: Image.Image):
        """画像を表示"""
        display_img = img.resize((Config.DISPLAY_SIZE, Config.DISPLAY_SIZE),
                                 Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(display_img)
        self.canvas.delete("all")
        self.canvas.create_image(Config.DISPLAY_SIZE // 2, Config.DISPLAY_SIZE // 2,
                                 image=photo)
        self.canvas.image = photo  # 参照を保持

    def _detect_by_dictionary(self):
        """辞書ベース検出"""
        if not self.current_image or not self.current_char:
            messagebox.showwarning("警告", "先に文字をレンダリングしてください")
            return

        # 構造情報を取得
        structure_info = self.dict_detector.detect_structure(self.current_char)

        if not structure_info:
            messagebox.showinfo("情報", f"文字「{self.current_char}」の構造情報が見つかりません")
            return

        # 抽出ガイドに基づいて抽出
        threshold = self.threshold_var.get()
        extracted = self.dict_detector.extract_by_guide(
            self.current_image,
            structure_info['extraction_guide'],
            threshold
        )

        # 結果を表示
        self._display_results(extracted, f"辞書ベース検出 - {structure_info['structure_type']}")

    def _detect_by_connected_components(self):
        """連結成分分析"""
        if not self.current_image:
            messagebox.showwarning("警告", "先に文字をレンダリングしてください")
            return

        # パラメータを更新
        self.component_analyzer.binary_threshold = self.threshold_var.get()
        self.component_analyzer.min_size = self.min_size_var.get()

        # 分析実行
        components = self.component_analyzer.analyze(self.current_image)

        # 結果を表示
        self._display_results(components, "連結成分分析")

    def _extract_common_radical(self):
        """複数文字から共通偏旁を抽出"""
        if not self.font_path:
            messagebox.showerror("エラー", "先にフォントを開いてください")
            return

        chars_str = self.multi_char_entry.get().strip()
        if len(chars_str) < 2:
            messagebox.showwarning("警告", "2文字以上入力してください")
            return

        chars = list(chars_str)

        # 共通偏旁を抽出
        results = self.common_extractor.extract_common_part_images(
            chars, self.font_path, self.dict_detector
        )

        if not results:
            # IDSベースで失敗した場合、共通構成要素名だけでも表示
            common = self.common_extractor.find_common_radical(chars)
            if common:
                messagebox.showinfo("結果", f"共通構成要素: {common}\n（画像抽出は未対応）")
            else:
                messagebox.showinfo("結果", "共通偏旁が見つかりませんでした")
            return

        # 結果を表示
        common_name = results[0]['common_part'] if results else "?"
        self._display_results(results, f"共通偏旁抽出: {common_name}")

    def _display_results(self, results: List[Dict], title: str):
        """結果を表示"""
        # 既存の結果をクリア
        for widget in self.result_frame.winfo_children():
            widget.destroy()

        self.result_images.clear()

        # タイトル
        ttk.Label(self.result_frame, text=title, font=("", 11, "bold")).pack(pady=5)

        if not results:
            ttk.Label(self.result_frame, text="成分が検出されませんでした").pack(pady=10)
            return

        # 各結果を表示
        for i, result in enumerate(results):
            frame = ttk.LabelFrame(self.result_frame, text=f"成分 {i+1}")
            frame.pack(fill=tk.X, padx=10, pady=5)

            # 情報テキスト
            info_text = ""

            if 'name' in result:
                info_text += f"領域: {result['name']}\n"
            if 'component' in result:
                info_text += f"構成要素: {result['component']}\n"
            if 'position' in result:
                info_text += f"位置: {result['position']}\n"
            if 'bbox' in result:
                bbox = result['bbox']
                info_text += f"bbox: ({bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]})\n"
            if 'size' in result:
                info_text += f"サイズ: {result['size']} px\n"
            if 'char' in result:
                info_text += f"元文字: {result['char']}\n"
            if 'region' in result:
                info_text += f"領域: {result['region']}\n"

            ttk.Label(frame, text=info_text, justify=tk.LEFT).pack(side=tk.LEFT, padx=10, pady=5)

            # 画像プレビュー
            if 'image' in result:
                img = result['image']
                # リサイズ
                max_size = 150
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.result_images.append(photo)  # 参照を保持

                img_label = ttk.Label(frame, image=photo)
                img_label.pack(side=tk.LEFT, padx=10, pady=5)

                # 保存ボタン
                save_btn = ttk.Button(frame, text="この成分を保存",
                                     command=lambda img=result['image'], idx=i: self._save_component(img, idx))
                save_btn.pack(side=tk.LEFT, padx=10, pady=5)

    def _save_component(self, img: Image.Image, index: int):
        """成分を保存"""
        file_path = filedialog.asksaveasfilename(
            title="成分を保存",
            defaultextension=".png",
            filetypes=[("PNG画像", "*.png"), ("すべて", "*.*")],
            initialfile=f"component_{index+1}.png"
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

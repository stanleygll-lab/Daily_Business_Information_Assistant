# -*- coding: utf-8 -*-
"""
Business Intelligence Infographic & Multi-Format Renderer
行业销售专版长图文与商机报告生成器
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import qrcode
from core.models import BusinessNewsItem


def get_char_width(c: str) -> int:
    return 2 if ord(c) > 0x2E80 else 1


def smart_chinese_wrap(text: str, max_width_chars: int = 28) -> List[str]:
    lines = []
    current_line = ""
    current_width = 0
    max_total_width = max_width_chars * 2

    tokens = re.split(r'(\s+)', text)
    for token in tokens:
        if not token:
            continue
        token_width = sum(get_char_width(c) for c in token)

        if token_width > max_total_width:
            for char in token:
                cw = get_char_width(char)
                if current_width + cw > max_total_width:
                    lines.append(current_line)
                    current_line = char
                    current_width = cw
                else:
                    current_line += char
                    current_width += cw
        elif current_width + token_width > max_total_width:
            if current_line:
                lines.append(current_line.rstrip())
            current_line = token.lstrip()
            current_width = sum(get_char_width(c) for c in current_line)
        else:
            current_line += token
            current_width += token_width

    if current_line:
        lines.append(current_line.rstrip())
    return lines


def load_best_font(size: int, is_bold: bool = False) -> ImageFont.ImageFont:
    font_candidates = [
        "C:\\Windows\\Fonts\\msyhbd.ttc" if is_bold else "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Songti.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


class SalesBriefingRenderer:
    """销售情报长图文与数据报告渲染器"""

    def __init__(self, app_config: Dict[str, Any], industries_config: Dict[str, Any], output_dir: Path):
        self.app_config = app_config
        self.industries_config = industries_config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_all(self, items: List[BusinessNewsItem]) -> Dict[str, str]:
        now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        prefix = self.app_config.get("title", "行业数智与安全商业动态").replace("📰 ", "").replace(" (销售专版)", "").strip()
        base_name = f"{prefix}_销售专版_{now_str}"

        # 1. 导出 JSON
        json_path = self.output_dir / f"{base_name}.json"
        self.export_json(items, json_path)

        # 2. 导出 Markdown 简报
        md_path = self.output_dir / f"{base_name}.md"
        self.export_markdown(items, md_path)

        # 3. 渲染销售专属信息流长图
        png_path = self.output_dir / f"{base_name}.png"
        self.render_infographic(items, png_path)

        return {
            "json": str(json_path),
            "markdown": str(md_path),
            "image": str(png_path)
        }

    def export_json(self, items: List[BusinessNewsItem], path: Path):
        data = [it.to_dict() for it in items]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def export_markdown(self, items: List[BusinessNewsItem], path: Path):
        title = self.app_config.get("title", "📰 行业数智与安全动态 (销售专版)")
        creator = self.app_config.get("creator", "商业情报分析助手")
        today = datetime.now().strftime("%Y年%m月%d日")

        lines = [
            f"# {title}",
            f"> 编制：**{creator}** | 日期：{today} | 聚焦 ToB 行业采购、重大招标与数智化大单\n",
            "---\n"
        ]

        grouped: Dict[str, List[BusinessNewsItem]] = {}
        for it in items:
            grouped.setdefault(it.industry, []).append(it)

        for ind_key, ind_conf in self.industries_config.items():
            ind_title = ind_conf.get("title", ind_key)
            ind_items = grouped.get(ind_key, [])

            lines.append(f"## {ind_title} ({len(ind_items)}条商机)")
            if not ind_items:
                lines.append("*(今日该行业暂无重点商机更新)*\n")
                continue

            for idx, it in enumerate(ind_items, 1):
                date_str = it.date.strftime("%m-%d") if isinstance(it.date, datetime) else str(it.date)[:10]
                bid_tag = " [💰重点标讯]" if it.is_bidding else ""
                lines.append(f"### {idx}. [{it.title}]({it.link}){bid_tag}")
                lines.append(f"- **情报来源**：`{it.source}` | **时间**：`{date_str}`")
                if it.summary:
                    lines.append(f"- **核心商业价值**：{it.summary}")
                lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def render_infographic(self, items: List[BusinessNewsItem], file_path: Path):
        width = int(self.app_config.get("image_width", 1000))
        y_pos = 60

        img = Image.new("RGB", (width, 2200), color="white")
        draw = ImageDraw.Draw(img)

        title_font = load_best_font(42, is_bold=True)
        subtitle_font = load_best_font(26, is_bold=True)
        body_font = load_best_font(24)
        summary_font = load_best_font(21)
        small_font = load_best_font(18)

        # 1. 标题
        main_title = self.app_config.get("title", "📰 行业数智与安全动态 (销售专版)")
        t_bbox = draw.textbbox((0, 0), main_title, font=title_font)
        draw.text(((width - (t_bbox[2] - t_bbox[0])) // 2, y_pos), main_title, fill="#0F172A", font=title_font)
        y_pos += 75

        # 2. 副标题
        creator = self.app_config.get("creator", "商业情报分析助手")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        sub_text = f"编制：{creator} | 专供一线销售、售前与生态团队 | {now_str}"
        sub_bbox = draw.textbbox((0, 0), sub_text, font=small_font)
        draw.text(((width - (sub_bbox[2] - sub_bbox[0])) // 2, y_pos), sub_text, fill="#64748B", font=small_font)
        y_pos += 55

        # 3. 销售提示框
        draw.rounded_rectangle([60, y_pos, width - 60, y_pos + 80], radius=8, fill="#FFFBEB", outline="#FDE68A", width=1)
        draw.text((80, y_pos + 16), "【商机开拓与扫码指引】", fill="#B45309", font=load_best_font(20, is_bold=True))
        draw.text((80, y_pos + 46), "每条商机右侧附带独立二维码，手机扫码即可直接直达招采公告与招标书原文。", fill="#92400E", font=small_font)
        y_pos += 115

        # 4. 按行业绘制
        grouped: Dict[str, List[BusinessNewsItem]] = {}
        for it in items:
            grouped.setdefault(it.industry, []).append(it)

        for ind_key, ind_conf in self.industries_config.items():
            ind_title = ind_conf.get("title", ind_key)
            bg_color = ind_conf.get("bg", "#F8FAFC")
            border_color = ind_conf.get("border", "#CBD5E1")
            text_color = ind_conf.get("text", "#1E293B")
            ind_items = grouped.get(ind_key, [])

            # 行业横幅卡片
            draw.rounded_rectangle([50, y_pos, width - 50, y_pos + 52], radius=6, fill=bg_color, outline=border_color, width=2)
            draw.text((70, y_pos + 12), f"{ind_title} ({len(ind_items)}条商机)", fill=text_color, font=subtitle_font)
            y_pos += 70

            if not ind_items:
                draw.text((75, y_pos), "（今日该行业暂无重点商机更新）", fill="#94A3B8", font=body_font)
                y_pos += 50
            else:
                for it in ind_items:
                    box_y = y_pos
                    box_height = 175
                    draw.rounded_rectangle([60, box_y, width - 60, box_y + box_height], radius=8, fill="#FAFAFA", outline="#E2E8F0", width=1)

                    # 标题
                    t_prefix = "【商机标讯】" if it.is_bidding else "【行业线索】"
                    t_full = f"{t_prefix}{it.title}"
                    lines = smart_chinese_wrap(t_full, max_width_chars=28)
                    display_lines = lines[:2]
                    if len(lines) > 2:
                        display_lines[-1] = display_lines[-1][:-1] + "..."

                    title_y = box_y + 14
                    for idx_l, line in enumerate(display_lines):
                        if idx_l == 0 and line.startswith(t_prefix):
                            draw.text((75, title_y), t_prefix, fill="#DC2626" if it.is_bidding else "#2563EB", font=body_font)
                            pw = draw.textbbox((0, 0), t_prefix, font=body_font)[2]
                            draw.text((75 + pw, title_y), line[len(t_prefix):], fill="#0F172A", font=body_font)
                        else:
                            draw.text((75, title_y), line, fill="#0F172A", font=body_font)
                        title_y += 30

                    # 摘要
                    s_prefix = "【商业事实】"
                    raw_summary = it.summary or "（点击扫码查看该商机招标公告及需求明细）"
                    s_lines = smart_chinese_wrap(f"{s_prefix}{raw_summary}", max_width_chars=32)
                    summary_y = title_y + 4

                    for idx_s, s_line in enumerate(s_lines[:2]):
                        if idx_s == 0 and s_line.startswith(s_prefix):
                            draw.text((75, summary_y), s_prefix, fill="#64748B", font=summary_font)
                            sw = draw.textbbox((0, 0), s_prefix, font=summary_font)[2]
                            draw.text((75 + sw, summary_y), s_line[len(s_prefix):], fill="#1E3A8A", font=summary_font)
                        else:
                            draw.text((75, summary_y), s_line, fill="#1E3A8A", font=summary_font)
                        summary_y += 26

                    # 来源与时间
                    date_str = it.date.strftime("%Y-%m-%d") if isinstance(it.date, datetime) else str(it.date)[:10]
                    meta = f"[{it.source}] {date_str}"
                    draw.text((75, box_y + box_height - 24), meta, fill="#64748B", font=small_font)

                    # 二维码
                    try:
                        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=4, border=1)
                        qr.add_data(it.link)
                        qr.make(fit=True)
                        qr_img = qr.make_image(fill_color="#0F172A", back_color="white").resize((115, 115))
                        img.paste(qr_img, (width - 180, box_y + 15))
                        draw.text((width - 165, box_y + 138), "扫码查阅", fill="#2563EB", font=small_font)
                    except Exception:
                        pass

                    y_pos += (box_height + 12)

                    if y_pos > img.height - 350:
                        new_img = Image.new("RGB", (width, img.height + 1600), color="white")
                        new_img.paste(img, (0, 0))
                        img = new_img
                        draw = ImageDraw.Draw(img)

            y_pos += 40

        final_img = img.crop((0, 0, width, min(y_pos + 60, img.height)))
        final_img.save(file_path, "PNG")
        print(f"  ✅ 销售专版长图文生成完成: {file_path}")

from pathlib import Path
import re
import fitz


TITLE_PATTERNS = [
    # 通用附录绩效表
    r"关键绩效指标",
    r"关键绩效表",
    r"关键绩效指标表",
    r"绩效指标一览",
    r"绩效指标表",
    r"绩效数据表",
    r"量化数据绩效表",
    r"量化绩效表",

    # ESG 数据表
    r"ESG\s*数据表",
    r"ESG\s*数据",
    r"ESG\s*关键绩效",
    r"ESG\s*数据(?:概览|汇总|一览)",

    # 附表 / 附录
    r"附表\s*\d*",
    r"附录\s*\d*",

    # 分维度标题
    r"经济维度",
    r"环境维度",
    r"社会维度",
    r"治理维度",
    r"环境绩效",
    r"社会绩效",
    r"治理绩效",

    # 表头类
    r"定量披露项",
    r"定量指标",
    r"指标",
    r"单位",
    r"20[0-3][0-9]年",
]


METRIC_WORDS = [
    # E 环境
    "温室气体",
    "范围一",
    "范围二",
    "能源",
    "能源消耗",
    "综合能源",
    "综合能耗",
    "电力",
    "用电",
    "耗电",
    "天然气",
    "柴油",
    "汽油",
    "煤",
    "水资源",
    "取水",
    "耗水",
    "用水量",
    "总用水",
    "新鲜水",
    "废水",
    "化学需氧量",
    "COD",
    "氨氮",
    "氮氧化物",
    "NOx",
    "二氧化硫",
    "SOx",
    "颗粒物",
    "废弃物",
    "危险废物",
    "危险废弃物",
    "无害废弃物",
    "环保投入",

    # S 社会
    "员工总数",
    "员工人数",
    "男性员工",
    "女性员工",
    "员工流失率",
    "培训",
    "安全生产",
    "工伤",
    "死亡",
    "研发投入",
    "研发人员",
    "专利",
    "客户投诉",
    "供应商",

    # G 治理
    "董事",
    "独立董事",
    "董事会",
    "股东大会",
    "监事会",
    "反腐",
    "反腐败",
    "反贪污",
    "反商业贿赂",
    "举报",
]


UNIT_WORDS = [
    "吨",
    "万吨",
    "吨标煤",
    "万吨标准煤",
    "吨二氧化碳当量",
    "万吨二氧化碳当量",
    "千瓦时",
    "万千瓦时",
    "立方米",
    "万立方米",
    "亿元",
    "万元",
    "元",
    "%",
    "人",
    "人次",
    "小时",
    "学时",
    "次",
    "件",
    "项",
    "起",
    "家",
]


INDEX_NEGATIVE_WORDS = [
    "指标索引",
    "内容索引",
    "GRI索引",
    "披露索引",
    "报告页码",
    "对应章节",
]


def normalize_text(text):
    if text is None:
        return ""

    return (
        str(text)
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("：", ":")
        .replace("，", ",")
        .lower()
    )


def unique_sorted(values):
    return sorted(set(values))


def expand_page_indices(page_indices, total_pages, before=1, after=2):
    """
    输入输出都是 0-indexed page_index。
    """
    expanded = set()

    for page_index in page_indices:
        for p in range(page_index - before, page_index + after + 1):
            if 0 <= p < total_pages:
                expanded.add(p)

    return sorted(expanded)


def sniff_esg_appendix(
    pdf_path,
    scan_ratio=0.4,
    min_score=12,
    top_k=12,
    expand_before=1,
    expand_after=2,
    strong_score=30,
    max_vlm_pages=14,
    tail_pages=12,
):
    """
    ESG 附录/数据表嗅探器。

    返回 expanded_page_numbers 使用自然页码：1, 2, 3...
    """

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    start_page = max(0, int(total_pages * (1 - scan_ratio)))
    candidates = []

    print(f"\n[Appendix Sniffer] 正在扫描文档末尾 {int(scan_ratio * 100)}% 页面...")

    for page_index in range(start_page, total_pages):
        page = doc[page_index]
        raw_text = page.get_text("text")
        text = normalize_text(raw_text)

        if not text:
            continue

        title_hits = [
            p for p in TITLE_PATTERNS
            if re.search(p, text, re.I)
        ]

        metric_hits = [
            w for w in METRIC_WORDS
            if normalize_text(w) in text
        ]

        unit_hits = [
            w for w in UNIT_WORDS
            if normalize_text(w) in text
        ]

        index_hits = [
            w for w in INDEX_NEGATIVE_WORDS
            if normalize_text(w) in text
        ]

        year_hits = sorted(set(re.findall(r"20[0-3][0-9]", text)))
        number_count = len(re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", text))

        score = 0
        reasons = []

        if title_hits:
            score += len(title_hits) * 12
            reasons.append(f"标题锚点命中: {title_hits[:8]}")

        if metric_hits:
            score += min(len(metric_hits), 15) * 4
            reasons.append(f"指标词命中: {metric_hits[:15]}")

        if unit_hits:
            score += min(len(unit_hits), 12) * 2
            reasons.append(f"单位词命中: {unit_hits[:12]}")

        if year_hits:
            score += min(len(year_hits), 3) * 4
            reasons.append(f"年份命中: {year_hits}")

        if "指标" in text and "单位" in text and re.search(r"20[0-3][0-9]", text):
            score += 18
            reasons.append("表头结构命中: 指标/单位/年份")

        if number_count >= 20:
            score += min(number_count // 20, 6) * 3
            reasons.append(f"数字密度较高: {number_count}")

        if page_index + 1 >= int(total_pages * 0.7):
            score += 5
            reasons.append("位于文档后30%")

        if index_hits:
            score -= 10
            reasons.append(f"疑似索引页扣分: {index_hits[:5]}")

        if score >= min_score:
            candidates.append(
                {
                    "page_index": page_index,
                    "page_number": page_index + 1,
                    "score": score,
                    "title_hits": title_hits,
                    "metric_hits": metric_hits,
                    "unit_hits": unit_hits,
                    "year_hits": year_hits,
                    "number_count": number_count,
                    "reasons": reasons,
                }
            )

    doc.close()

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]

    # 1. 强候选页
    strong_candidates = [c for c in candidates if c["score"] >= strong_score]

    if strong_candidates:
        base_indices = [c["page_index"] for c in strong_candidates]
    else:
        base_indices = [c["page_index"] for c in candidates[:3]]

    expanded_indices = expand_page_indices(
        base_indices,
        total_pages=total_pages,
        before=expand_before,
        after=expand_after,
    )

    # 2. 兜底：最后 tail_pages 页强制加入
    tail_start = max(0, total_pages - tail_pages)
    tail_indices = list(range(tail_start, total_pages))

    merged_indices = unique_sorted(expanded_indices + tail_indices)

    # 3. 限制最多送入 VLM 的页数
    # 优先保留强候选附近页 + 最后若干页
    if len(merged_indices) > max_vlm_pages:
        priority_indices = []

        # 先保留 strong / top candidate 附近页
        priority_indices.extend(expanded_indices)

        # 再保留尾页
        priority_indices.extend(tail_indices)

        priority_indices = unique_sorted(priority_indices)

        # 如果还是太多，优先取最后 max_vlm_pages 页
        # 因为 ESG 数据表通常在附录末尾
        if len(priority_indices) > max_vlm_pages:
            merged_indices = priority_indices[-max_vlm_pages:]
        else:
            merged_indices = priority_indices

    expanded_page_numbers = [p + 1 for p in merged_indices]

    print("\n命中候选页：")
    for item in candidates:
        print(f"  第 {item['page_number']} 页 | score={item['score']}")
        for reason in item["reasons"]:
            print(f"    - {reason}")

    print("\n建议送入多模态模型的页码：")
    print(expanded_page_numbers)

    return {
        "found": bool(expanded_page_numbers),
        "total_pages": total_pages,
        "candidates": candidates,
        "expanded_page_numbers": expanded_page_numbers,
        "candidate_pages": expanded_page_numbers,
        "scan_ratio": scan_ratio,
        "scan_start_page": start_page + 1,
    }


def render_pdf_pages_to_images(pdf_path, page_numbers, output_dir, zoom=3.5):
    """
    将 PDF 指定页渲染为图片。

    针对孚日股份这类“双页合成在一张 PDF 页面里”的报告：
    - 先保存整页图；
    - 再额外切出 left / right 两张半页图；
    - VLM 会分别识别，更容易抽出表格。
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_paths = []

    with fitz.open(pdf_path) as doc:
        for page_number in page_numbers:
            idx = page_number - 1

            if idx < 0 or idx >= len(doc):
                continue

            page = doc[idx]
            rect = page.rect

            matrix = fitz.Matrix(zoom, zoom)

            # 1. 保存整页
            pix = page.get_pixmap(
                matrix=matrix,
                alpha=False,
            )

            full_img = output_dir / f"page_{page_number}.png"
            pix.save(str(full_img))
            image_paths.append(str(full_img))

            # 2. 保存左半页
            left_rect = fitz.Rect(
                rect.x0,
                rect.y0,
                rect.x0 + rect.width / 2,
                rect.y1,
            )

            left_pix = page.get_pixmap(
                matrix=matrix,
                clip=left_rect,
                alpha=False,
            )

            left_img = output_dir / f"page_{page_number}_left.png"
            left_pix.save(str(left_img))
            image_paths.append(str(left_img))

            # 3. 保存右半页
            right_rect = fitz.Rect(
                rect.x0 + rect.width / 2,
                rect.y0,
                rect.x1,
                rect.y1,
            )

            right_pix = page.get_pixmap(
                matrix=matrix,
                clip=right_rect,
                alpha=False,
            )

            right_img = output_dir / f"page_{page_number}_right.png"
            right_pix.save(str(right_img))
            image_paths.append(str(right_img))

    return image_paths
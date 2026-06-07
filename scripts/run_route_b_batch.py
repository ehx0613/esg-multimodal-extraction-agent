import csv
import os
from pathlib import Path

from config.settings import RAW_DATA_DIR, REPORTS_DIR, OUTPUT_DIR
from pipeline.text_pipeline import ESGTextPipeline
from pipeline.batch_pipeline import safe_name
from utils.raw_pdf_utils import list_raw_pdfs


def find_route_a_report_dir(pdf_stem: str) -> Path:
    """
    浼樺厛鎵惧埌璺嚎 A 宸茬粡鐢熸垚鐨勭洰褰曘€?
    鍏煎锛?
    1. 001_xxx
    2. xxx
    """

    candidates = [
        p for p in REPORTS_DIR.iterdir()
        if p.is_dir()
        and (
            p.name == pdf_stem
            or p.name.endswith(pdf_stem)
            or pdf_stem in p.name
        )
        and (p / "standard_esg_results.csv").exists()
    ]

    if candidates:
        candidates.sort(key=lambda p: len(p.name))
        return candidates[0]

    return REPORTS_DIR / pdf_stem


def main():
    pdfs = list_raw_pdfs(RAW_DATA_DIR)
    if os.getenv("ESG_BATCH_TOP_LEVEL_ONLY", "false").lower() == "true":
        pdfs = sorted(path for path in RAW_DATA_DIR.glob("*.pdf") if path.is_file())

    if not pdfs:
        raise FileNotFoundError(f"娌℃湁鍦?{RAW_DATA_DIR} 鎵惧埌 PDF")

    rows = []

    top_level_only = os.getenv("ESG_BATCH_TOP_LEVEL_ONLY", "false").lower() == "true"

    for idx, pdf in enumerate(pdfs, start=1):
        print("\n" + "=" * 100)
        print(f"[{idx}/{len(pdfs)}] Route B: {pdf.name}")
        print("=" * 100)

        if top_level_only:
            report_dir = REPORTS_DIR / f"{idx:03d}_{safe_name(pdf.stem)}"
        else:
            report_dir = find_route_a_report_dir(pdf.stem)
        report_dir.mkdir(parents=True, exist_ok=True)

        try:
            summary = ESGTextPipeline(report_dir).run(pdf)

            rows.append({
                "pdf_name": pdf.name,
                "success": True,
                "route_b_available": summary.get("route_b_available"),
                "target_fields": summary.get("target_fields"),
                "matched_fields": summary.get("matched_fields"),
                "quant_target_fields": summary.get("quantitative_fallback", {}).get("target_fields"),
                "quant_matched_fields": summary.get("quantitative_fallback", {}).get("matched_fields"),
                "total_llm_calls": summary.get("total_llm_calls"),
                "reason": summary.get("reason", ""),
                "output_dir": str(report_dir),
            })

        except Exception as e:
            rows.append({
                "pdf_name": pdf.name,
                "success": False,
                "route_b_available": False,
                "target_fields": 0,
                "matched_fields": 0,
                "quant_target_fields": 0,
                "quant_matched_fields": 0,
                "total_llm_calls": 0,
                "reason": str(e),
                "output_dir": str(report_dir),
            })

    out_path = OUTPUT_DIR / "route_b_batch_summary.csv"

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "pdf_name",
            "success",
            "route_b_available",
            "target_fields",
            "matched_fields",
            "quant_target_fields",
            "quant_matched_fields",
            "total_llm_calls",
            "reason",
            "output_dir",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nRoute B batch summary saved: {out_path}")


if __name__ == "__main__":
    main()

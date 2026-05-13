import csv
from pathlib import Path

from config.settings import RAW_DATA_DIR, REPORTS_DIR, OUTPUT_DIR
from pipeline.text_pipeline import ESGTextPipeline


def find_route_a_report_dir(pdf_stem: str) -> Path:
    """
    优先找到路线 A 已经生成的目录。
    兼容：
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
    pdfs = sorted(RAW_DATA_DIR.glob("*.pdf"))

    if not pdfs:
        raise FileNotFoundError(f"没有在 {RAW_DATA_DIR} 找到 PDF")

    rows = []

    for idx, pdf in enumerate(pdfs, start=1):
        print("\n" + "=" * 100)
        print(f"[{idx}/{len(pdfs)}] Route B: {pdf.name}")
        print("=" * 100)

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
            "reason",
            "output_dir",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nRoute B batch summary saved: {out_path}")


if __name__ == "__main__":
    main()
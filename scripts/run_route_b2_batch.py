import csv
import os

from config.settings import OUTPUT_DIR, RAW_DATA_DIR, REPORTS_DIR
from pipeline.batch_pipeline import safe_name
from pipeline.quant_text_pipeline import ESGQuantTextPipeline
from scripts.run_route_b_batch import find_route_a_report_dir
from utils.raw_pdf_utils import list_raw_pdfs


def main():
    pdfs = list_raw_pdfs(RAW_DATA_DIR)
    if os.getenv("ESG_BATCH_TOP_LEVEL_ONLY", "false").lower() == "true":
        pdfs = sorted(path for path in RAW_DATA_DIR.glob("*.pdf") if path.is_file())

    start_index = 1
    start = os.getenv("ESG_BATCH_START")
    limit = os.getenv("ESG_BATCH_LIMIT")
    if start:
        start_index = int(start)
        pdfs = pdfs[start_index - 1:]
    if limit:
        pdfs = pdfs[:int(limit)]

    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in {RAW_DATA_DIR}")

    rows = []
    top_level_only = os.getenv("ESG_BATCH_TOP_LEVEL_ONLY", "false").lower() == "true"

    total = start_index + len(pdfs) - 1
    for idx, pdf in enumerate(pdfs, start=start_index):
        print("\n" + "=" * 100)
        print(f"[{idx}/{total}] Route B2: {pdf.name}")
        print("=" * 100)

        if top_level_only:
            report_dir = REPORTS_DIR / f"{idx:03d}_{safe_name(pdf.stem)}"
        else:
            report_dir = find_route_a_report_dir(pdf.stem)
        report_dir.mkdir(parents=True, exist_ok=True)

        try:
            summary = ESGQuantTextPipeline(report_dir).run(pdf)
            rows.append(
                {
                    "pdf_name": pdf.name,
                    "success": True,
                    "route_b2_available": summary.get("route_b2_available"),
                    "industry": summary.get("industry"),
                    "target_fields": summary.get("target_fields"),
                    "matched_fields": summary.get("matched_fields"),
                    "llm_calls": summary.get("llm_calls"),
                    "skipped_by_industry": summary.get("skipped_by_industry"),
                    "skipped_by_unlikely": summary.get("skipped_by_unlikely"),
                    "skipped_by_budget": summary.get("skipped_by_budget"),
                    "reason": summary.get("reason", ""),
                    "output_dir": str(report_dir),
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "pdf_name": pdf.name,
                    "success": False,
                    "route_b2_available": False,
                    "industry": "",
                    "target_fields": 0,
                    "matched_fields": 0,
                    "llm_calls": 0,
                    "skipped_by_industry": 0,
                    "skipped_by_unlikely": 0,
                    "skipped_by_budget": 0,
                    "reason": str(exc),
                    "output_dir": str(report_dir),
                }
            )

    out_path = OUTPUT_DIR / "route_b2_batch_summary.csv"
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "pdf_name",
            "success",
            "route_b2_available",
            "industry",
            "target_fields",
            "matched_fields",
            "llm_calls",
            "skipped_by_industry",
            "skipped_by_unlikely",
            "skipped_by_budget",
            "reason",
            "output_dir",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nRoute B2 batch summary saved: {out_path}")


if __name__ == "__main__":
    main()

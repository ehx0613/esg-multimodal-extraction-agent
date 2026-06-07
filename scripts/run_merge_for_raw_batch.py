import csv
from pathlib import Path

from config.settings import OUTPUT_DIR, RAW_DATA_DIR, REPORTS_DIR
from pipeline.merge_pipeline import ESGMergePipeline
from utils.raw_pdf_utils import list_raw_pdfs


def find_report_dir_for_pdf(pdf_stem: str) -> Path | None:
    candidates = [
        p for p in REPORTS_DIR.iterdir()
        if p.is_dir()
        and pdf_stem in p.name
        and (p / "standard_esg_results.csv").exists()
    ]

    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def main():
    pdfs = list_raw_pdfs(RAW_DATA_DIR)

    if not pdfs:
        raise FileNotFoundError(f"娌℃湁鍦?{RAW_DATA_DIR} 鎵惧埌 PDF")

    report_dirs = []
    missing = []

    for pdf in pdfs:
        report_dir = find_report_dir_for_pdf(pdf.stem)
        if report_dir is None:
            missing.append(pdf.name)
            continue
        report_dirs.append((pdf.name, report_dir))

    if not report_dirs:
        raise FileNotFoundError("娌℃湁鎵惧埌涓庡綋鍓?data/raw/*.pdf 瀵瑰簲鐨勮矾绾?A 杈撳嚭鐩綍銆?")

    rows = []

    for idx, (pdf_name, report_dir) in enumerate(report_dirs, start=1):
        print("\n" + "=" * 100)
        print(f"[{idx}/{len(report_dirs)}] Merge: {pdf_name}")
        print("=" * 100)

        try:
            summary = ESGMergePipeline(report_dir).run()

            rows.append({
                "pdf_name": pdf_name,
                "report_name": report_dir.name,
                "success": True,
                "total_fields": summary.get("total_fields"),
                "route_a_extracted_fields": summary.get("route_a_extracted_fields"),
                "route_b_matched_fields": summary.get("route_b_matched_fields"),
                "route_b_filled_fields": summary.get("route_b_filled_fields"),
                "merged_extracted_fields": summary.get("merged_extracted_fields"),
                "missing_fields": summary.get("missing_fields"),
                "coverage_rate": summary.get("coverage_rate"),
                "output_dir": str(report_dir),
                "error": "",
            })
        except Exception as e:
            rows.append({
                "pdf_name": pdf_name,
                "report_name": report_dir.name,
                "success": False,
                "total_fields": "",
                "route_a_extracted_fields": "",
                "route_b_matched_fields": "",
                "route_b_filled_fields": "",
                "merged_extracted_fields": "",
                "missing_fields": "",
                "coverage_rate": "",
                "output_dir": str(report_dir),
                "error": str(e),
            })

    for pdf_name in missing:
        rows.append({
            "pdf_name": pdf_name,
            "report_name": "",
            "success": False,
            "total_fields": "",
            "route_a_extracted_fields": "",
            "route_b_matched_fields": "",
            "route_b_filled_fields": "",
            "merged_extracted_fields": "",
            "missing_fields": "",
            "coverage_rate": "",
            "output_dir": "",
            "error": "route_a_output_not_found",
        })

    out_path = OUTPUT_DIR / "merge_for_raw_batch_summary.csv"

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "pdf_name",
            "report_name",
            "success",
            "total_fields",
            "route_a_extracted_fields",
            "route_b_matched_fields",
            "route_b_filled_fields",
            "merged_extracted_fields",
            "missing_fields",
            "coverage_rate",
            "output_dir",
            "error",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nMerge-for-raw batch summary saved: {out_path}")


if __name__ == "__main__":
    main()

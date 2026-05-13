# scripts/run_merge_batch.py

import csv
from pathlib import Path

from config.settings import REPORTS_DIR, OUTPUT_DIR
from pipeline.merge_pipeline import ESGMergePipeline


def main():
    report_dirs = [
        p for p in REPORTS_DIR.iterdir()
        if p.is_dir() and (p / "standard_esg_results.csv").exists()
    ]

    if not report_dirs:
        raise FileNotFoundError("没有找到任何路线 A 输出目录。")

    report_dirs.sort(key=lambda p: p.name)

    rows = []

    for idx, report_dir in enumerate(report_dirs, start=1):
        print("\n" + "=" * 100)
        print(f"[{idx}/{len(report_dirs)}] Merge: {report_dir.name}")
        print("=" * 100)

        try:
            summary = ESGMergePipeline(report_dir).run()

            rows.append({
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

    out_path = OUTPUT_DIR / "merge_batch_summary.csv"

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
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

    print(f"\nMerge batch summary saved: {out_path}")


if __name__ == "__main__":
    main()
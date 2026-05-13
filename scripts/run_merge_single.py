# scripts/run_merge_single.py

from pathlib import Path

from config.settings import REPORTS_DIR
from pipeline.merge_pipeline import ESGMergePipeline


def find_latest_report_dir() -> Path:
    report_dirs = [
        p for p in REPORTS_DIR.iterdir()
        if p.is_dir() and (p / "standard_esg_results.csv").exists()
    ]

    if not report_dirs:
        raise FileNotFoundError("没有找到包含 standard_esg_results.csv 的报告目录。")

    report_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return report_dirs[0]


def main():
    report_dir = find_latest_report_dir()

    ESGMergePipeline(report_dir).run()

    print(f"Merge 输出目录: {report_dir}")


if __name__ == "__main__":
    main()
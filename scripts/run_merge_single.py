import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge one ESG report directory.")
    parser.add_argument(
        "report_dir",
        nargs="?",
        help="Report directory under output/reports, or an absolute path. Defaults to the latest report.",
    )
    return parser.parse_args()


def resolve_report_dir(value: str | None) -> Path:
    if not value:
        return find_latest_report_dir()

    path = Path(value)
    if not path.is_absolute():
        direct = path.resolve()
        path = direct if direct.exists() else REPORTS_DIR / value

    if not path.is_dir():
        raise FileNotFoundError(f"报告目录不存在: {path}")
    if not (path / "standard_esg_results.csv").exists():
        raise FileNotFoundError(f"报告目录缺少 standard_esg_results.csv: {path}")
    return path


def main():
    args = parse_args()
    report_dir = resolve_report_dir(args.report_dir)

    ESGMergePipeline(report_dir).run()

    print(f"Merge 输出目录: {report_dir}")


if __name__ == "__main__":
    main()

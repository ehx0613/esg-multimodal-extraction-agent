import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "output" / "reports"


def main():
    report_dirs = [
        p for p in REPORTS_DIR.iterdir()
        if p.is_dir() and (p / "all_table_rows.json").exists()
    ]

    if not report_dirs:
        raise FileNotFoundError("没有找到包含 all_table_rows.json 的报告目录。")

    print(f"发现 {len(report_dirs)} 个已有报告目录，开始批量重跑 Schema 匹配。")

    for idx, report_dir in enumerate(report_dirs, start=1):
        print("\n" + "=" * 80)
        print(f"[{idx}/{len(report_dirs)}] {report_dir.name}")
        print("=" * 80)

        subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.rerun_schema_match",
                str(report_dir),
            ],
            cwd=PROJECT_ROOT,
            check=False,
        )

    print("\n批量 Schema 重匹配完成。")


if __name__ == "__main__":
    main()
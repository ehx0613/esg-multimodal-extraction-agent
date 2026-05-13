from pathlib import Path

from config.settings import RAW_DATA_DIR, REPORTS_DIR
from pipeline.appendix_pipeline import ESGAppendixPipeline


SELECTED_FILES = [
    #"000858_五_粮_液_2024_五_粮_液：2024年度环境、社会及公司治理（ESG）报告.pdf",
    "002083_孚日股份_2025_孚日股份：社会责任报告.pdf",
]


def main():
    for filename in SELECTED_FILES:
        pdf_path = RAW_DATA_DIR / filename

        if not pdf_path.exists():
            print(f"❌ 找不到 PDF: {pdf_path}")
            continue

        report_dir = REPORTS_DIR / pdf_path.stem

        print("\n" + "=" * 100)
        print(f"开始处理: {filename}")
        print("=" * 100)

        ESGAppendixPipeline(report_dir).run(pdf_path)

        print(f"✅ 完成: {filename}")
        print(f"输出目录: {report_dir}")


if __name__ == "__main__":
    main()
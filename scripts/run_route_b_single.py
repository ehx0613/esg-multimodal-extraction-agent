from pathlib import Path

from config.settings import RAW_DATA_DIR, REPORTS_DIR
from pipeline.text_pipeline import ESGTextPipeline


def main():
    pdfs = sorted(RAW_DATA_DIR.glob("*.pdf"))

    if not pdfs:
        raise FileNotFoundError(f"没有在 {RAW_DATA_DIR} 找到 PDF")

    pdf = pdfs[0]

    report_dir = REPORTS_DIR / pdf.stem
    report_dir.mkdir(parents=True, exist_ok=True)

    ESGTextPipeline(report_dir).run(pdf)

    print(f"Route B 输出目录: {report_dir}")


if __name__ == "__main__":
    main()
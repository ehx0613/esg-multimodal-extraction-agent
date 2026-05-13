import sys
from pathlib import Path
from config.settings import RAW_DATA_DIR, REPORTS_DIR
from pipeline.appendix_pipeline import ESGAppendixPipeline


def find_first_pdf():
    pdfs = sorted(RAW_DATA_DIR.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"未在 {RAW_DATA_DIR} 找到 PDF")
    return pdfs[0]

if __name__ == "__main__":
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else find_first_pdf()
    ESGAppendixPipeline(REPORTS_DIR / pdf.stem).run(pdf)

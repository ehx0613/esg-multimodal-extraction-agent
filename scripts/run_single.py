import sys
from pathlib import Path

from config.settings import RAW_DATA_DIR, REPORTS_DIR
from pipeline.appendix_pipeline import ESGAppendixPipeline
from utils.raw_pdf_utils import find_raw_pdf_by_name, list_raw_pdfs


def find_first_pdf():
    pdfs = list_raw_pdfs(RAW_DATA_DIR)
    if not pdfs:
        raise FileNotFoundError(f"未在 {RAW_DATA_DIR} 找到 PDF")
    return pdfs[0]


def resolve_pdf_arg(arg: str) -> Path:
    pdf = Path(arg)
    if pdf.exists():
        return pdf

    resolved = find_raw_pdf_by_name(RAW_DATA_DIR, arg)
    if resolved is None:
        raise FileNotFoundError(f"未在 {RAW_DATA_DIR} 找到 PDF: {arg}")
    return resolved


if __name__ == "__main__":
    pdf = resolve_pdf_arg(sys.argv[1]) if len(sys.argv) > 1 else find_first_pdf()
    ESGAppendixPipeline(REPORTS_DIR / pdf.stem).run(pdf)

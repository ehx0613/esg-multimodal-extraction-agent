import argparse
from pathlib import Path

from config.settings import RAW_DATA_DIR, REPORTS_DIR
from pipeline.quant_text_pipeline import ESGQuantTextPipeline
from scripts.run_route_b_batch import find_route_a_report_dir
from utils.raw_pdf_utils import find_raw_pdf_by_name, list_raw_pdfs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compatibility command: run only the Route B quantitative fallback."
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        help="PDF path or file name under data/raw. Defaults to the first raw PDF.",
    )
    parser.add_argument(
        "--pdf",
        dest="pdf_option",
        help="PDF path or file name under data/raw.",
    )
    return parser.parse_args()


def resolve_pdf_arg(value: str | None) -> Path:
    if not value:
        pdfs = list_raw_pdfs(RAW_DATA_DIR)
        if not pdfs:
            raise FileNotFoundError(f"No PDF found under {RAW_DATA_DIR}")
        return pdfs[0]

    pdf = Path(value)
    if pdf.exists():
        return pdf

    resolved = find_raw_pdf_by_name(RAW_DATA_DIR, value)
    if resolved is None:
        raise FileNotFoundError(f"PDF not found: {value}")
    return resolved


def main() -> None:
    args = parse_args()
    pdf = resolve_pdf_arg(args.pdf_option or args.pdf)

    report_dir = find_route_a_report_dir(pdf.stem)
    report_dir.mkdir(parents=True, exist_ok=True)

    ESGQuantTextPipeline(report_dir).run(pdf)

    print(f"Route B2 output dir: {report_dir}")


if __name__ == "__main__":
    main()

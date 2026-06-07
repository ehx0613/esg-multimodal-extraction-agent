import argparse
import json
from pathlib import Path

from config.settings import RAW_DATA_DIR, REPORTS_DIR
from pipeline.unified_pipeline import UnifiedESGPipeline
from utils.raw_pdf_utils import find_raw_pdf_by_name, list_raw_pdfs


def resolve_pdf(value: str | None) -> Path:
    if not value:
        pdfs = list_raw_pdfs(RAW_DATA_DIR)
        if not pdfs:
            raise FileNotFoundError(f"No PDF found under {RAW_DATA_DIR}")
        return pdfs[0]
    path = Path(value)
    if path.exists():
        return path
    resolved = find_raw_pdf_by_name(RAW_DATA_DIR, value)
    if resolved is None:
        raise FileNotFoundError(f"PDF not found: {value}")
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the unified ESG extraction pipeline.")
    parser.add_argument("pdf", nargs="?", help="PDF path or name under data/raw.")
    parser.add_argument("--force-visual", action="store_true", help="Do not reuse existing visual outputs.")
    parser.add_argument(
        "--mode",
        choices=["fast", "balanced", "deep"],
        default="fast",
        help="Extraction budget mode. Defaults to fast.",
    )
    args = parser.parse_args()
    pdf = resolve_pdf(args.pdf)
    summary = UnifiedESGPipeline(REPORTS_DIR / pdf.stem, run_mode=args.mode).run(
        pdf,
        reuse_visual_results=not args.force_visual,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

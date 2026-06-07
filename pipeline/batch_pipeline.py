import csv, os, re, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from config.settings import RAW_DATA_DIR, REPORTS_DIR, OUTPUT_DIR
from pipeline.appendix_pipeline import ESGAppendixPipeline
from utils.raw_pdf_utils import list_raw_pdfs


def safe_name(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name)[:120]


def run_one(i, total, pdf):
    out = REPORTS_DIR / f"{i:03d}_{safe_name(pdf.stem)}"
    try:
        print(f"\n[{i}/{total}] {pdf.name}")
        state = ESGAppendixPipeline(out).run(pdf)
        s = state.get("validation_summary", {})
        return {"pdf_file": pdf.name, "status": "success", "error": "", "report_dir": str(out), "appendix_found": state.get("appendix_found"), "candidate_pages": ";".join(map(str, state.get("candidate_pages", []))), **s}
    except Exception as e:
        out.mkdir(parents=True, exist_ok=True)
        (out / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
        return {"pdf_file": pdf.name, "status": "failed", "error": str(e), "report_dir": str(out), "appendix_found": "", "candidate_pages": "", "total_fields": 0, "extracted_fields": 0, "missing_fields": 0, "coverage_rate": 0, "raw_row_count": 0, "unknown_metrics": 0, "needs_route_b2": "", "route_b2_reason": ""}


def write_summary(rows):
    path = OUTPUT_DIR / "batch_summary.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["pdf_file", "status", "error", "report_dir", "appendix_found", "candidate_pages", "raw_row_count", "total_fields", "extracted_fields", "missing_fields", "coverage_rate", "unknown_metrics", "needs_route_b2", "route_b2_reason"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def run_batch():
    pdfs = list_raw_pdfs(RAW_DATA_DIR)
    if os.getenv("ESG_BATCH_TOP_LEVEL_ONLY", "false").lower() == "true":
        pdfs = sorted(path for path in RAW_DATA_DIR.glob("*.pdf") if path.is_file())
    start_index = 1
    limit = os.getenv("ESG_BATCH_LIMIT")
    start = os.getenv("ESG_BATCH_START")
    if start:
        start_index = int(start)
        pdfs = pdfs[start_index - 1:]
    if limit:
        pdfs = pdfs[:int(limit)]
    if not pdfs:
        raise FileNotFoundError(f"未在 {RAW_DATA_DIR} 找到 PDF")
    workers = int(os.getenv("ESG_BATCH_WORKERS", "2"))
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        total = start_index + len(pdfs) - 1
        fs = [ex.submit(run_one, i, total, p) for i, p in enumerate(pdfs, start_index)]
        for f in as_completed(fs):
            rows.append(f.result())
            write_summary(sorted(rows, key=lambda x: x["pdf_file"]))
    write_summary(sorted(rows, key=lambda x: x["pdf_file"]))
    print(f"Batch summary saved to: {OUTPUT_DIR / 'batch_summary.csv'}")

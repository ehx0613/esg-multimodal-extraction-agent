from scripts.run_single import find_first_pdf
from config.settings import REPORTS_DIR
from pipeline.appendix_pipeline import ESGAppendixPipeline

pdf = find_first_pdf()
ESGAppendixPipeline(REPORTS_DIR / pdf.stem).run(pdf)
